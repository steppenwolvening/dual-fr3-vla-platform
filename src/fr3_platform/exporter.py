"""Explicit train-only joint-position + width profile for pinned LeRobot v3.0.

This 16-component profile is NOT a LingBot action representation.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from .contracts import SIDES, JOINTS, require
from .data import DatasetReader, validate, causal_latest, atomic_json

PROFILE = [f'{s}.joint{i}.rad' for s in SIDES for i in range(1,8)] + [f'{s}.opening_width.m' for s in SIDES]


def training_rows(root, label, fps, tolerance_ns, *, allowed_splits=('train',), camera_stream=None):
    require(label in ('requested','sent','accepted'), 'explicit training label required')
    require(type(fps) is int and 0 < fps <= 1000, 'fps')
    require(type(tolerance_ns) is int and tolerance_ns >= 0, 'alignment tolerance')
    report = validate(root)
    require(report['ok'], json.dumps(report))
    reader = DatasetReader(root)
    require(reader.meta['split'] in allowed_splits, 'this exporter fits train-only statistics; validation/test export BLOCKED pending pinned train statistics reuse')
    events = list(reader)
    states = [e for e in events if e['kind']=='state']
    images = [e for e in events if e['kind']=='rgb' and (camera_stream is None or e['stream']==camera_stream)]
    commands = [e for e in events if e['kind']==label]
    require(bool(states) and bool(images) and bool(commands), 'missing state/RGB/selected label')
    require(len({e['stream'] for e in images})==1, 'select explicit camera mapping before multicamera export')
    by_obs = {}
    for e in commands:
        obs = e['payload']['command']['observation_id']
        require(obs not in by_obs, 'ambiguous multiple labels for observation')
        by_obs[obs]=e
    start,_ = reader.common_time(states[0])
    rows=[]
    for i, state in enumerate(states):
        ts,uncertainty=reader.common_time(state)
        # This first profile rejects irregular observations instead of hiding resampling.
        require(abs(ts-start-round(i*1e9/fps))+uncertainty <= 100_000, 'irregular state sampling; explicit resampler required')
        require(state['id'] in by_obs, 'observation has no selected action label')
        ce = by_obs[state['id']]
        ct,cu=reader.common_time(ce)
        require(ct-cu >= ts+uncertainty and ct+cu-(ts-uncertainty) <= tolerance_ns, 'action timing outside causal horizon')
        c=ce['payload']['command']
        require(c['kind']=='joint_position', 'profile requires joint position targets')
        rgb=causal_latest(reader,images,state,tolerance_ns)
        values,actions=[],[]
        for side in SIDES:
            a=state['payload']['arms'][side]
            require(a['position']['status']!='missing', 'missing joint state')
            values.extend(a['position']['value']);actions.extend(c['arms'][side]['target'])
        for side in SIDES:
            g=state['payload']['arms'][side]['gripper']
            require(g['status']!='missing', 'missing gripper width')
            require('gripper' in c['arms'][side], 'explicit gripper target required')
            values.append(g['value']);actions.append(c['arms'][side]['gripper']['target'])
        rows.append({'state':values,'action':actions,'rgb':rgb,'source_time_ns':ts,'observation_id':state['id'],'command_event_id':ce['id']})
    return reader, rows


def export_lerobot(source, destination, *, label, fps, tolerance_ns, pin_file):
    destination=Path(destination)
    require(not destination.exists(), 'export must use a new output directory')
    reader,rows=training_rows(source,label,fps,tolerance_ns)
    # Set process-local offline flags BEFORE optional libraries import.
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['HF_DATASETS_OFFLINE']='1'
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    require(importlib.metadata.version('lerobot')=='0.4.4', 'expected LeRobot 0.4.4')
    import numpy as np
    import lerobot.datasets.lerobot_dataset as implementation
    from lerobot.datasets.lerobot_dataset import LeRobotDataset, CODEBASE_VERSION
    pins=json.loads(Path(pin_file).read_text())
    actual=hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest()
    require(actual==pins['loader_sha256'], 'LeRobot loader source differs from audited pin')
    require(CODEBASE_VERSION=='v3.0', 'expected LeRobot dataset format v3.0')
    shape=tuple(rows[0]['rgb']['payload']['shape'])
    require(all(tuple(r['rgb']['payload']['shape'])==shape for r in rows), 'RGB shape changed')
    features={'observation.state':{'dtype':'float32','shape':(16,), 'names':PROFILE},
              'action':{'dtype':'float32','shape':(16,), 'names':PROFILE},
              'observation.images.camera':{'dtype':'image','shape':shape,'names':['height','width','channels']}}
    dataset=LeRobotDataset.create(repo_id='local/dual-fr3-canonical',root=destination,fps=fps,features=features,
                                 robot_type='dual_fr3_canonical_profile_v1',use_videos=False)
    try:
        for row in rows:
            rgb=np.frombuffer(reader.blob(row['rgb']),dtype=np.uint8).reshape(shape).copy()
            dataset.add_frame({'observation.state':np.asarray(row['state'],dtype=np.float32),
                               'action':np.asarray(row['action'],dtype=np.float32),
                               'observation.images.camera':rgb,'task':reader.meta['task']})
        dataset.save_episode()
    finally: dataset.finalize()
    loaded=LeRobotDataset(repo_id='local/dual-fr3-canonical',root=destination,download_videos=False)
    require(len(loaded)==len(rows), 'reader frame count mismatch')
    for i,row in enumerate(rows):
        item=loaded[i]
        require(tuple(item['action'].shape)==(16,) and tuple(item['observation.state'].shape)==(16,), 'reader shape mismatch')
        require(np.allclose(item['action'].numpy(),row['action']), 'reader action mismatch')
        require(np.allclose(item['observation.state'].numpy(),row['state']), 'reader state mismatch')
        expected=np.frombuffer(reader.blob(row['rgb']),dtype=np.uint8).reshape(shape).transpose(2,0,1)/255.0
        require(np.allclose(item['observation.images.camera'].numpy(),expected,atol=1e-6), 'reader RGB pixel mismatch')
    mapping={'schema':'fr3.lerobot-export/1','profile':'explicit_joint_position_width_16_NOT_LingBot',
             'loader_version':'0.4.4','codebase_version':CODEBASE_VERSION,'loader_sha256':actual,'source_episode_id':reader.meta['episode_id'],
             'source_events_sha256':hashlib.sha256((Path(source)/'events.jsonl').read_bytes()).hexdigest(),
             'synthetic':reader.meta['synthetic'],'split':'train','label':label,'fields':PROFILE,
             'image':'raw RGB to lossless PNG; no resize/crop; reader CHW float32 /255',
             'clock_maps':reader.meta['clocks'],'alignment_tolerance_ns':tolerance_ns,
             'observation_timing':'obs_t from measured/estimated state; image upper time bound <= observation lower bound',
             'action_timing':'selected command after obs_t within tolerance, bound by observation_id; no measured-state substitution',
             'sampling':'regular observed state rate only; irregular input rejected; no interpolation',
             'depth_tactile':'preserved ONLY in canonical source; excluded from policy tensors',
             'normalization':'LeRobot stats computed only on this train episode; no normalization applied by exporter; not production statistics',
             'rows':[{k:v for k,v in row.items() if k not in ('state','action','rgb')} for row in rows],
             'validation':'PASS_OFFLINE_REAL_LEROBOT_READER'}
    atomic_json(destination/'canonical_mapping.json',mapping)
    return {'status':'PASS_OFFLINE','reader':'LeRobotDataset 0.4.4 / v3.0','frames':len(loaded),
            'state_shape':list(loaded[0]['observation.state'].shape),'action_shape':list(loaded[0]['action'].shape),
            'image_shape':list(loaded[0]['observation.images.camera'].shape),'synthetic':reader.meta['synthetic']}
