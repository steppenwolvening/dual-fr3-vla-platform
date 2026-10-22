#!/usr/bin/env python3
"""Actual Isaac Lab 6.1.14 replay runner; NOT_RUN until separate execution approval.
No USD remote assets: converts the local official FR3 URDF. Never loads weights.
"""
import argparse,json,sys,time,copy
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
p=argparse.ArgumentParser();p.add_argument('episode',type=Path);p.add_argument('output',type=Path);p.add_argument('--execute',action='store_true');p.add_argument('--max-frames',type=int,default=20)
a=p.parse_args();assert 0<a.max_frames<=60
if not a.execute:
 print(json.dumps({'status':'NOT_RUN','scene':'local official dual FR3 URDF + Franka Hand','max_frames':a.max_frames,'mode':'REPLAY, set measured joints; not independent control evaluation','requires':'approved installed Isaac Lab execution, potentially GPU context and shader-cache writes'}));sys.exit(0)
a.output.mkdir(parents=True,exist_ok=False)
from isaaclab.app import AppLauncher
app=AppLauncher(headless=True,device='cpu',kit_args=f'--portable --portable-root={a.output.resolve()}/kit --/log/file={a.output.resolve()}/isaac.log').app
try:
 import torch
 import isaaclab.sim as sim_utils
 from isaaclab.assets import Articulation,ArticulationCfg
 from isaaclab.actuators import ImplicitActuatorCfg
 from fr3_platform.data import DatasetReader
 from fr3_platform.contracts import RobotState,JOINTS
 sim=sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=.002,device='cpu'))
 spawn=sim_utils.UrdfFileCfg(asset_path=str(root/'assets/fr3_reference/dual_fr3.urdf'),usd_dir=str(a.output/'usd'),usd_file_name='dual_fr3.usd',fix_base=True,merge_fixed_joints=False,collision_from_visuals=False,self_collision=True,rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=True))
 cfg=ArticulationCfg(prim_path='/World/DualFR3',spawn=spawn,actuators={'arms':ImplicitActuatorCfg(joint_names_expr=['.*_fr3_joint[1-7]'],stiffness=400.,damping=40.),'hands':ImplicitActuatorCfg(joint_names_expr=['.*_fr3_finger_joint[1-2]'],stiffness=200.,damping=5.)})
 robot=Articulation(cfg);sim.reset();robot.update(.002)
 reader=DatasetReader(a.episode);events=[e for e in reader if e['kind']=='state'][:a.max_frames]
 assert events
 names=list(robot.joint_names);bodies=list(robot.body_names)
 expected=[f'{s}_fr3_joint{i}' for s in JOINTS for i in range(1,8)]+[f'{s}_fr3_finger_joint{i}' for s in JOINTS for i in (1,2)]
 assert set(expected)<=set(names),names
 # Retain fixed TCP links in conversion and fail rather than substitute hand frames.
 tcp_names={s:f'{s}_fr3_hand_tcp' for s in JOINTS};assert all(n in bodies for n in tcp_names.values()),bodies
 records=[]
 for e in events:
  state=RobotState(e['payload']).validate().payload;t0=time.monotonic_ns()
  q=robot.data.joint_pos.torch.clone();v=torch.zeros_like(q)
  for s in JOINTS:
   for i,value in enumerate(state['arms'][s]['position']['value'],1):q[0,names.index(f'{s}_fr3_joint{i}')]=value
   for i in (1,2):q[0,names.index(f'{s}_fr3_finger_joint{i}')]=state['arms'][s]['gripper']['value']/2
  robot.write_joint_position_to_sim_index(position=q);robot.write_joint_velocity_to_sim_index(velocity=v);robot.set_joint_position_target_index(target=q);robot.write_data_to_sim();sim.step();robot.update(.002)
  measured=copy.deepcopy(state);measured['state_id']='isaac-'+state['state_id'];measured['controller_status']='isaac_replay';measured['safety_status']='simulation_only_no_hardware'
  for s in JOINTS:
   arm=measured['arms'][s];arm['position']['value']=[float(robot.data.joint_pos.torch[0,names.index(f'{s}_fr3_joint{i}')]) for i in range(1,8)]
   arm['velocity']['value']=[float(robot.data.joint_vel.torch[0,names.index(f'{s}_fr3_joint{i}')]) for i in range(1,8)]
   arm['gripper']['value']=sum(float(robot.data.joint_pos.torch[0,names.index(f'{s}_fr3_finger_joint{i}')]) for i in (1,2))
   bi=bodies.index(tcp_names[s]);pos=robot.data.body_pos_w.torch[0,bi].tolist();quat=robot.data.body_quat_w.torch[0,bi].tolist()
   arm['tcp']={'position_m':pos,'quaternion_xyzw':quat[1:]+quat[:1],'frame':'world','child_frame':f'{s}_tcp','provenance':'Isaac PhysX FK; common official URDF virtual bases'}
  RobotState(measured).validate()
  records.append({'reference_state_id':state['state_id'],'reference_stamp':state['stamp'],'source':'isaac_replay','measured':measured,'receive_monotonic_ns':t0,'update_latency_ns':time.monotonic_ns()-t0})
 with (a.output/'states.jsonl').open('w') as f:
  for row in records:f.write(json.dumps(row)+'\n')
 (a.output/'run.json').write_text(json.dumps({'status':'EXECUTED_REQUIRES_COMPARISON','mode':'REPLAY','frames':len(records),'joint_names':names,'tcp_names':tcp_names},indent=2))
finally:app.close()
