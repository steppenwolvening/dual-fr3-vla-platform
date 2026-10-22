"""Multi-camera LeRobot v3 exports with immutable train-derived normalization stats.

The audited 0.4.4 SDK unconditionally fits episode statistics. A process-local,
locked override supplies frozen training statistics for evaluation saves, then
restores the SDK function. No evaluation data enters the fitting implementation.
This shim is source-hash pinned and must be reviewed when upgrading LeRobot.
"""
from pathlib import Path
import copy
import hashlib
import importlib.metadata
import json
import threading
from .contracts import require
from .data import DatasetReader, causal_latest, atomic_json, read_json
from .exporter import training_rows,PROFILE

_STATS_LOCK=threading.Lock()


def export_split(episodes,destination,*,split,cameras,label,fps,tolerance_ns,training_stats=None,pin_file=None):
    require(split in ('train','validation','test'),'split')
    require(bool(cameras) and len(set(cameras.values()))==len(cameras),'explicit unique camera mapping')
    require((training_stats is None)==(split=='train'),'train fits statistics; evaluation requires fixed training statistics')
    dest=Path(destination);require(not dest.exists(),'new export destination required')
    import numpy as np
    import lerobot.datasets.lerobot_dataset as sdk
    from lerobot.datasets.utils import write_stats,write_info,serialize_dict
    pin=read_json(pin_file or Path(__file__).resolve().parents[2]/'environments/lerobot-reader-pin.json')
    require(importlib.metadata.version('lerobot')=='0.4.4' and hashlib.sha256(Path(sdk.__file__).read_bytes()).hexdigest()==pin['loader_sha256'],'audited LeRobot source pin mismatch')
    frozen=None
    if training_stats:
        frozen=read_json(training_stats)
        require(frozen['split']=='train' and frozen['fields']==PROFILE and frozen['cameras']==cameras and frozen['label']==label and frozen['fps']==fps,'training stats profile mismatch')
        require(frozen['normalization_fit']=='train_only','untrusted statistics origin')
        fixed={k:{stat:np.asarray(v) for stat,v in values.items()} for k,values in frozen['stats'].items()}
    prepared=[];features=None;source_ids=[]
    for episode in episodes:
        r,rows=training_rows(episode,label,fps,tolerance_ns,allowed_splits=(split,),camera_stream=next(iter(cameras.values())))
        require(r.meta['episode_id'] not in source_ids,'duplicate episode id');source_ids.append(r.meta['episode_id'])
        all_events=list(r);states={e['id']:e for e in all_events if e['kind']=='state'}
        streams={stream:[e for e in all_events if e['kind']=='rgb' and e['stream']==stream] for stream in cameras.values()}
        for row in rows:
            row['images']={name:causal_latest(r,streams[stream],states[row['observation_id']],tolerance_ns) for name,stream in cameras.items()}
        ft={'observation.state':{'dtype':'float32','shape':(16,),'names':PROFILE},'action':{'dtype':'float32','shape':(16,),'names':PROFILE}}
        for name,img in rows[0]['images'].items():ft['observation.images.'+name]={'dtype':'image','shape':tuple(img['payload']['shape']),'names':['height','width','channels']}
        require(features is None or features==ft,'episode feature mismatch');features=ft
        prepared.append((r,rows))
    require(bool(prepared),'empty split')
    if frozen:require(not set(source_ids)&set(frozen['source_episode_ids']),'train/eval episode leakage')
    dataset=sdk.LeRobotDataset.create(repo_id='local/dual-fr3-'+split,root=dest,fps=fps,features=features,robot_type='dual_fr3_reference',use_videos=False)
    fit_calls=0
    try:
        for r,rows in prepared:
            for row in rows:
                frame={'observation.state':np.asarray(row['state'],np.float32),'action':np.asarray(row['action'],np.float32),'task':r.meta['task']}
                for name,e in row['images'].items():frame['observation.images.'+name]=np.frombuffer(r.blob(e),np.uint8).reshape(e['payload']['shape']).copy()
                dataset.add_frame(frame)
            with _STATS_LOCK:
                original=sdk.compute_episode_stats
                if frozen:sdk.compute_episode_stats=lambda *args,**kwargs:copy.deepcopy(fixed)
                try:
                    dataset.save_episode()
                    if not frozen:fit_calls+=1
                finally:sdk.compute_episode_stats=original
        if frozen:
            dataset.meta.stats=copy.deepcopy(fixed);write_stats(dataset.meta.stats,dest)
        dataset.meta.info['splits']={split:f'0:{len(prepared)}'};write_info(dataset.meta.info,dest)
    finally:dataset.finalize()
    loaded=sdk.LeRobotDataset('local/dual-fr3-'+split,root=dest,download_videos=False)
    index=0
    for r,rows in prepared:
        for row in rows:
            item=loaded[index];index+=1
            require(np.allclose(item['action'].numpy(),row['action']) and np.allclose(item['observation.state'].numpy(),row['state']),'reader state/action mismatch')
            for name,e in row['images'].items():
                expected=np.frombuffer(r.blob(e),np.uint8).reshape(e['payload']['shape']).transpose(2,0,1)/255
                require(np.allclose(item['observation.images.'+name].numpy(),expected,atol=1e-6),'camera association/pixel mismatch')
    stats=serialize_dict(loaded.meta.stats)
    if frozen:require(stats==frozen['stats'],'evaluation stats changed')
    stats_record={'schema':'fr3.train-stats/1','split':'train','normalization_fit':'train_only','fields':PROFILE,'cameras':cameras,'label':label,'fps':fps,
                  'source_episode_ids':source_ids if not frozen else frozen['source_episode_ids'],'stats':stats}
    atomic_json(dest/'training_statistics.json',stats_record)
    stats_hash=hashlib.sha256((dest/'training_statistics.json').read_bytes()).hexdigest()
    manifest={'schema':'fr3.export/2','split':split,'cameras':cameras,'fields':PROFILE,'label':label,'fps':fps,'tolerance_ns':tolerance_ns,
              'source_episode_ids':source_ids,'contains_synthetic':any(r.meta.get('contains_synthetic',r.meta['synthetic']) for r,_ in prepared),
              'stats_sha256':stats_hash,'stats_fitting_calls':fit_calls,'stats_source':'this train split' if not frozen else 'external immutable training_statistics.json',
              'image_processing':'lossless RGB PNG; no resize; reader CHW /255','depth_tactile':'canonical only','irregular_sampling':'REJECTED; no hidden interpolation',
              'semantics':'absolute joint positions rad left7/right7 + absolute opening widths m left/right; NOT assumed model output semantics',
              'rows':[{'episode_id':r.meta['episode_id'],'observation_id':row['observation_id'],'command_event_id':row['command_event_id'],'source_time_ns':row['source_time_ns'],'images':{name:e['id'] for name,e in row['images'].items()}} for r,rows in prepared for row in rows]}
    atomic_json(dest/'canonical_mapping.json',manifest)
    return {'status':'PASS_OFFLINE','split':split,'reader_frames':len(loaded),'cameras':list(cameras),'stats_sha256':stats_hash,'stats_fitting_calls':fit_calls}
