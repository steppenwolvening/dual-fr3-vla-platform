#!/usr/bin/env python3
import sys,copy,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fr3_platform.teleop_se3 import DualPoseMapper
from fr3_platform.contracts import ContractError
r=Rotation.from_euler('z',90,degrees=True).as_matrix();m=DualPoseMapper(r,'test');poses={s:np.eye(4) for s in ('left','right')}
def frame(seq):return {'schema':'fr3.vr-pose/1','sequence':seq,'common_time_ns':seq*10_000_000+1,'tracking_origin':'test','hands':{s:{'world_from_grip':np.eye(4).tolist(),'tracking':True,'deadman':True,'opening_width_m':.04} for s in poses}}
f=frame(0);m.update(f,poses,1)
f=frame(1);f['hands']['left']['world_from_grip'][0][3]=.01
out=m.update(f,poses,f['common_time_ns']);assert np.allclose(out['targets']['left'][:3,3],[0,.01,0])
f=frame(2);f['hands']['left']['clutch']=True;f['hands']['left']['world_from_grip'][0][3]=.02
out=m.update(f,poses,f['common_time_ns']);assert np.allclose(out['targets']['left'],poses['left'])
f=frame(3);f['hands']['left']['world_from_grip'][0][3]=.5
out=m.update(f,poses,f['common_time_ns']);assert out['active']==['right'] and out['release_reasons']['left']=='pose jump'
f=frame(4);out=m.update(f,poses,f['common_time_ns']+100_000_001);assert out['active']==[]
try:m.update(f,poses,f['common_time_ns']);raise AssertionError('sequence accepted')
except ContractError:pass
print('PASS_OFFLINE: nonidentity frame mapping, clutch, jump, independent arm, stale and ordering')
