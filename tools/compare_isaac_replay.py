#!/usr/bin/env python3
import sys,json,argparse,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fr3_platform.data import DatasetReader
from fr3_platform.contracts import RobotState
p=argparse.ArgumentParser();p.add_argument('episode',type=Path);p.add_argument('isaac_output',type=Path);a=p.parse_args()
ref={e['payload']['state_id']:e['payload'] for e in DatasetReader(a.episode) if e['kind']=='state'}
rows=[json.loads(x) for x in (a.isaac_output/'states.jsonl').read_text().splitlines()];seen=set();qerr=[];perr=[];rerr=[];gerr=[];lat=[]
for row in rows:
 key=row['reference_state_id'];assert key not in seen and key in ref;seen.add(key)
 original=ref[key];measured=RobotState(row['measured']).validate().payload
 assert row['reference_stamp']==original['stamp']
 for side in ('left','right'):
  x=original['arms'][side];y=measured['arms'][side]
  qerr.extend(abs(a-b) for a,b in zip(x['position']['value'],y['position']['value']));gerr.append(abs(x['gripper']['value']-y['gripper']['value']))
  perr.append(math.dist(x['tcp']['position_m'],y['tcp']['position_m']))
  dot=abs(sum(a*b for a,b in zip(x['tcp']['quaternion_xyzw'],y['tcp']['quaternion_xyzw'])));rerr.append(2*math.acos(min(1.,dot)))
 lat.append(row['update_latency_ns']/1e6)
assert rows
result={'status':'PASS_SIM' if max(qerr)<1e-3 and max(perr)<1e-3 and max(rerr)<5e-3 and max(gerr)<1e-3 and len(rows)==len(ref) else 'FAIL','mode':'REPLAY','frames':len(rows),'missing_frames':len(ref)-len(seen),'max_joint_error_rad':max(qerr),'max_tcp_position_error_m':max(perr),'max_tcp_orientation_error_rad':max(rerr),'max_gripper_width_error_m':max(gerr),'mean_apply_update_latency_ms':sum(lat)/len(lat),'clock_alignment':'explicit replay logical source stamp; not live clock synchronization','shadow':'NOT_RUN','independent_dynamics':'NOT_RUN'}
(root/'validation/phase2/isaac_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(0 if result['status']=='PASS_SIM' else 1)
