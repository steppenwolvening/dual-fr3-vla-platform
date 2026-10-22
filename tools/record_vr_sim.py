#!/usr/bin/env python3
"""Record full dual-arm simulation episodes driven by synthetic controller SE(3) poses."""
import sys,json,time,copy,argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fr3_platform.mujoco_backend import DualFR3,MinkIK
from fr3_platform.teleop_se3 import DualPoseMapper
from fr3_platform.sensor_sources import SyntheticCamera,SyntheticTactile
from fr3_platform.control import OfflineExecutor
from fr3_platform.contracts import VERSION,JOINTS,ContractError
from fr3_platform.data import Recorder,validate,replay

p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
reports=[];episodes={};fps=10
for split in ('train','validation','test'):
    backend=DualFR3();ik=MinkIK(backend);mapper=DualPoseMapper(np.eye(3),'synthetic-local-floor');executor=OfflineExecutor(backend,backend.limits(),clock='simulation')
    sources=[SyntheticCamera('head',10),SyntheticCamera('left_wrist',70),SyntheticCamera('right_wrist',130),SyntheticTactile()]
    stream_sources={'state':'simulation','requested':'simulation','sent':'simulation','vr':'synthetic','authority':'simulation','tactile':'synthetic'}
    for name in ('head','left_wrist','right_wrist'):
        for mode in ('rgb','depth'):stream_sources[name+'.'+mode]='synthetic'
    meta={'schema':VERSION,'episode_id':'vr-sim-'+split,'synthetic':False,'contains_synthetic':True,'stream_sources':stream_sources,
          'task':'Move both FR3 tools along a small free-space demonstration','outcome':'simulation_only','split':split,'code_version':'0.2.0-dev','config_version':'fr3-reference-v1','calibration_version':'VIRTUAL_NOT_LAB',
          'streams':list(stream_sources),'clocks':{'simulation':{'scale':1.,'offset_ns':0,'uncertainty_ns':0,'common_clock':'episode_monotonic','provenance':'simulation clock, synthetic sensors scheduled on same time','valid_from_ns':0,'valid_to_ns':100_000_000_000}}}
    path=a.output/split;episodes[split]=[str(path.resolve())];latencies=[];max_residual=0.;contacts=0
    state=backend.state()
    with Recorder(path,meta,capacity=256) as rec:
        for k in range(20):
            t=state['stamp']['source_ns'];stamp=state['stamp']
            poses={s:backend.pose_matrix(s) for s in ('left','right')};hands={}
            for side,sgn in [('left',1),('right',-1)]:
                pose=np.eye(4);pose[:3,3]=[.002*np.sin(k/20*np.pi),sgn*.001*np.sin(k/20*np.pi),.002*np.sin(k/20*np.pi)]
                pose[:3,:3]=Rotation.from_rotvec([0,0,sgn*.005*np.sin(k/20*np.pi)]).as_matrix()
                hands[side]={'world_from_grip':pose.tolist(),'tracking':True,'deadman':True,'clutch':False,'recenter':False,'opening_width_m':.04+.001*np.sin(k/20*np.pi)}
            frame={'schema':'fr3.vr-pose/1','tracking_origin':'synthetic-local-floor','common_time_ns':t,'sequence':k,'hands':hands}
            start=time.perf_counter_ns();mapped=mapper.update(frame,poses,t);q,ir=ik.solve(mapped['targets']);latencies.append(time.perf_counter_ns()-start)
            max_residual=max(max_residual,max(x['position_m'] for x in ir['residuals'].values()))
            executor.acquire('vr',t,200_000_000)
            command={'stamp':{**stamp,'source_ns':t+10_000_000,'received_ns':t+10_000_000},'command_id':f'vr-{k}','observation_id':state['state_id'],'owner':'vr','kind':'joint_position','side_order':['left','right'],
                     'arms':{s:{'joint_names':JOINTS[s],'unit':'rad','target':[float(q[backend.model.jnt_qposadr[j]]) for j in backend.joints[s]],'gripper':{'quantity':'opening_width','unit':'m','target':mapped['opening_width_m'][s]}} for s in ('left','right')}}
            def e(kind,stream,payload,event_stamp=stamp,source='simulation'):
                return {'schema':VERSION,'id':f'{stream}-{k}','kind':kind,'stream':stream,'source':source,'stamp':event_stamp,'payload':payload}
            assert rec.submit(e('state','state',state))
            assert rec.submit(e('vr','vr',{'tracking':True,'deadman':True,'tracking_origin':'synthetic-local-floor','frame':frame,'mapping_latency_ns':latencies[-1]},source='synthetic'))
            assert rec.submit(e('authority','authority',{'reason':'synthetic VR lease','owner':'vr'}))
            for source in sources:
                for ev,blob in source.frames(stamp,k):assert rec.submit(ev,blob)
            assert rec.submit(e('requested','requested',{'command':copy.deepcopy(command)},command['stamp']))
            sent=executor.submit(command,state,t+10_000_000)
            assert rec.submit(e('sent','sent',sent,command['stamp']))
            state=backend.step(50);contacts+=len(backend.contacts())
        # Independent-side deadman and stale/tracking loss checks on the actual mapper.
        current={s:backend.pose_matrix(s) for s in ('left','right')}
        fault=copy.deepcopy(frame);fault['sequence']+=1;fault['common_time_ns']+=100_000_000;fault['hands']['left']['tracking']=False
        result=mapper.update(fault,current,fault['common_time_ns']);assert result['active']==['right']
        fault['sequence']+=1;fault['common_time_ns']+=100_000_000
        result=mapper.update(fault,current,fault['common_time_ns']+101_000_000);assert result['active']==[]
        executor.watchdog(fault['common_time_ns']+101_000_000,tracking=False);backend.hold();assert executor.owner is None
    report=validate(path);assert report['ok'],report;assert contacts==0
    assert len(list(replay(path)))==240
    reports.append({'split':split,'status':'PASS_SIM','frames':20,'events':report['events'],'max_ik_position_residual_m':max_residual,'penetrating_contacts':contacts,'mean_mapping_ik_latency_ms':float(np.mean(latencies)/1e6),'tracking_loss_timeout':'PASS','VR_DEVICE':'NOT_RUN','cameras':'3 synthetic RGB-D streams; not real D405','tactile':'synthetic raw; protocol unknown'})
manifest={'episodes':episodes,'cameras':{'head':'head.rgb','left_wrist':'left_wrist.rgb','right_wrist':'right_wrist.rgb'},'label':'sent','fps':fps,'tolerance_ns':20_000_000}
(a.output/'splits.json').write_text(json.dumps(manifest,indent=2)+'\n');(root/'validation/phase2/vr_sim.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
