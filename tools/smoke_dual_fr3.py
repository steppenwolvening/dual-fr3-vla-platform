#!/usr/bin/env python3
import sys
from pathlib import Path
import json
import numpy as np
import xml.etree.ElementTree as ET
from scipy.spatial.transform import Rotation
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fr3_platform.mujoco_backend import DualFR3,MinkIK
from fr3_platform.contracts import ContractError,JOINTS
b=DualFR3();ik=MinkIK(b)
# Independently compose the expanded official URDF tree, compare TCP with MuJoCo FK.
urdf=ET.parse(root/'assets/fr3_reference/dual_fr3.urdf').getroot();joints=urdf.findall('joint')
world={'world':np.eye(4)}
while len(world)<len(urdf.findall('link')):
 old=len(world)
 for j in joints:
  parent=j.find('parent').get('link');child=j.find('child').get('link')
  if parent not in world or child in world:continue
  origin=j.find('origin');t=np.eye(4)
  if origin is not None:
   t[:3,3]=[float(x) for x in origin.get('xyz','0 0 0').split()];t[:3,:3]=Rotation.from_euler('xyz',[float(x) for x in origin.get('rpy','0 0 0').split()]).as_matrix()
  motion=np.eye(4)
  if j.get('type') in ('revolute','prismatic'):
   q=b.data.qpos[b.model.joint(j.get('name')).qposadr[0]];axis=np.array([float(x) for x in j.find('axis').get('xyz').split()])
   if j.get('type')=='revolute':motion[:3,:3]=Rotation.from_rotvec(axis*q).as_matrix()
   else:motion[:3,3]=axis*q
  world[child]=world[parent]@t@motion
 assert len(world)>old,'URDF unresolved frame'
fk={s:float(np.max(np.abs(world[f'{s}_fr3_hand_tcp']-b.pose_matrix(s)))) for s in ('left','right')}
assert max(fk.values())<1e-8
results=[]
for sides in [('left',),('right',),('left','right')]:
 targets={s:b.pose_matrix(s).copy() for s in sides}
 for s,t in targets.items():t[:3,3]+=[.015,.005 if s=='left' else -.005,.01];t[:3,:3]=Rotation.from_rotvec([0,0,.02]).as_matrix()@t[:3,:3]
 q,report=ik.solve(targets);results.append({'arms':sides,**report});b.set_state(q);assert not b.contacts()
# Reject an illegal configuration.
bad=b.data.qpos.copy();bad[0]=10
try:b.set_state(bad);raise AssertionError('joint limit bypassed')
except ContractError:pass
# Bounded dynamics track a slow joint trajectory, preserving gripper target mapping.
initial=b.data.qpos.copy();max_error=0.;collisions=0
for k in range(120):
 state=b.state();arms={}
 for s in ('left','right'):
  targets=[float(initial[b.model.jnt_qposadr[j]]+.004*np.sin(k/120*np.pi*2)) for j in b.joints[s]]
  arms[s]={'joint_names':JOINTS[s],'unit':'rad','target':targets,'gripper':{'quantity':'opening_width','unit':'m','target':.04+.01*np.sin(k/120*np.pi*2)}}
 c={'stamp':state['stamp'],'command_id':f'c{k}','observation_id':state['state_id'],'owner':'replay','kind':'joint_position','side_order':['left','right'],'arms':arms}
 b.send(c);measured=b.step(5);collisions+=len(b.contacts())
 max_error=max(max_error,max(abs(q-v) for s in ('left','right') for q,v in zip(arms[s]['target'],measured['arms'][s]['position']['value'])))
assert max_error<.03 and collisions==0
out={'status':'PASS_SIM','scope':'official FR3+Franka Hand virtual reference, not lab calibration','nq':b.model.nq,'actuators':b.model.nu,'fk_max_matrix_error':fk,'ik':results,'trajectory':{'control_frames':120,'physics_steps':600,'max_joint_tracking_error_rad':max_error,'penetrating_contacts':collisions},'limit_rejection':'PASS','gripper_mapping':'width_m/2 to each of two opposing fingers','thresholds':{'fk_matrix':1e-8,'ik_position_m':1e-3,'ik_rotation_rad':5e-3,'trajectory_joint_rad':.03}}
(root/'validation/phase2').mkdir(exist_ok=True,parents=True);(root/'validation/phase2/mujoco_mink.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
