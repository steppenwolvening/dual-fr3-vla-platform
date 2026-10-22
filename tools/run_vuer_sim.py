#!/usr/bin/env python3
"""Quest/Vuer -> dual SE3 mapper -> real Mink -> MuJoCo (simulation only).
NOT_RUN live: Vuer installation, trusted TLS and actual controller mapping pending.
"""
import argparse,json,time,sys,asyncio
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
p=argparse.ArgumentParser();p.add_argument('config',type=Path);p.add_argument('--execute',action='store_true');a=p.parse_args()
cfg=json.loads(a.config.read_text())
if not a.execute:print(json.dumps({'status':'NOT_RUN','transport':'Vuer MotionControllers (OpenTeleVision transport family)','config':cfg,'hardware_output':False}));sys.exit(0)
from vuer import Vuer
from vuer.schemas import MotionControllers
import numpy as np
from fr3_platform.vuer_input import controller_frame
from fr3_platform.teleop_se3 import DualPoseMapper
from fr3_platform.mujoco_backend import DualFR3,MinkIK
from fr3_platform.control import OfflineExecutor
from fr3_platform.contracts import JOINTS
from fr3_platform.vla import action_command
assert cfg['review_status']=='SIMULATION_MAPPING_REVIEWED'
backend=DualFR3();ik=MinkIK(backend);mapper=DualPoseMapper(np.asarray(cfg['robot_from_tracking']),cfg['tracking_origin']);executor=OfflineExecutor(backend,backend.limits());seq=0;last_ns=0;latest=None
# No tunnelling or certificate creation. Explicit TLS files are user-provided and ignored by Git.
app=Vuer(host=cfg['bind_host'],cert=cfg['tls_cert'],key=cfg['tls_key'],queue_len=1)
@app.add_handler('CONTROLLER_MOVE')
async def receive(event,session):
 global latest,seq
 now=time.monotonic_ns();latest=controller_frame(event.value,sequence=seq,received_ns=now,origin=cfg['tracking_origin'],buttons=cfg['buttons']);seq+=1
@app.spawn(start=True)
async def main(session):
 global latest,last_ns
 session.upsert @ MotionControllers(stream=True,key='fr3-controllers',left=True,right=True)
 previous_tick=time.monotonic_ns()
 while True:
  await asyncio.sleep(.01);now=time.monotonic_ns();old=executor.owner;executor.watchdog(now)
  if old and executor.owner is None:backend.hold()
  if latest is not None:
   frame=latest;latest=None;state=backend.state();state['stamp'].update(source_ns=previous_tick,received_ns=now,clock='host_monotonic',receive_clock='host_monotonic')
   try:
    poses={s:backend.pose_matrix(s) for s in JOINTS};mapped=mapper.update(frame,poses,now)
    if not mapped['active']:executor.release('VR tracking/deadman');backend.hold()
    else:
     q,_=ik.solve(mapped['targets']);physical=sum([[float(q[backend.model.jnt_qposadr[j]]) for j in backend.joints[s]] for s in JOINTS],[])+[mapped['opening_width_m'].get(s,state['arms'][s]['gripper']['value']) for s in JOINTS]
     cmd=action_command(physical,state,now_ns=now,sequence=frame['sequence'],clock='host_monotonic',command_id='vr-live-'+str(frame['sequence']));cmd['owner']='vr'
     executor.acquire('vr',now,100_000_000);executor.submit(cmd,state,now)
   except Exception as e:executor.release(str(e));backend.hold();print(json.dumps({'status':'REJECTED','reason':str(e)}),file=sys.stderr)
  backend.step(5)
  if backend.contacts():executor.watchdog(now,estop=True);backend.hold()
  previous_tick=now
