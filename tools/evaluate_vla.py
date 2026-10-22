#!/usr/bin/env python3
"""Common actual-model MuJoCo evaluation; process-isolated model environment.

Default is a plan. --execute-model must only be used after model/GPU approval.
This task is free-space tool hold, not grasp success or real-robot performance.
"""
import argparse,sys,json,time,subprocess,selectors,os,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
p=argparse.ArgumentParser();p.add_argument('--worker-python',required=True);p.add_argument('--model',choices=['pi05_native','lingbot_vla_v2'],required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--profile',required=True);p.add_argument('--robot-config');p.add_argument('--norm-stats');p.add_argument('--runtime-source');p.add_argument('--output',type=Path,required=True);p.add_argument('--execute-model',action='store_true');p.add_argument('--frames',type=int,default=20);a=p.parse_args();assert 0<a.frames<=100
if not a.execute_model:print(json.dumps({'status':'NOT_RUN','model':a.model,'task':'hold both tools at initial free-space poses','scene':'official dual FR3 reference','frames':a.frames,'fps':10,'success':'completed, zero collisions/violations, max tool displacement < 0.02 m','gpu_and_rendering':'requires approval','hardware':False}));sys.exit(0)
import numpy as np,mujoco
from fr3_platform.mujoco_backend import DualFR3
from fr3_platform.vla import ChunkScheduler,SEMANTICS
from fr3_platform.control import OfflineExecutor
# Add simulation cameras to a transient model; no hardware extrinsics claimed.
spec=mujoco.MjSpec.from_file(str(root/'assets/fr3_reference/dual_fr3.xml'))
spec.worldbody.add_light(pos=[0,0,3],dir=[0,0,-1])
spec.worldbody.add_camera(name='head',pos=[2,-2,2],xyaxes=[.707,.707,0,-.408,.408,.816])
for s in ('left','right'):spec.body(f'{s}_fr3_hand').add_camera(name=s+'_wrist',pos=[0,0,.06],quat=[0,1,0,0])
a.output.mkdir(parents=True,exist_ok=False)
backend=DualFR3(model=spec.compile());executor=OfflineExecutor(backend,backend.limits(),clock='simulation');scheduler=ChunkScheduler(executor)
renderer=mujoco.Renderer(backend.model,height=224,width=224)
cmd=[a.worker_python,'-B',str(root/'tools/model_worker.py'),'--model',a.model,'--checkpoint',a.checkpoint,'--profile',a.profile,'--execute-model']
for key in ('robot_config','norm_stats','runtime_source'):
 if getattr(a,key):cmd+=['--'+key.replace('_','-'),getattr(a,key)]
log=(a.output/'model.log').open('w');proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1);selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
def response(timeout):
 if not selector.select(timeout):raise TimeoutError('model process deadline')
 line=proc.stdout.readline()
 if not line:raise RuntimeError('model process exited; inspect model.log')
 return json.loads(line)
latency=[];end_to_end=[];errors=[];collisions=0;completed=0;violations=[];began=time.monotonic_ns();targets={s:backend.pose_matrix(s)[:3,3].copy() for s in ('left','right')}
try:
 assert response(180)['status']=='MODEL_LOADED'
 for i in range(a.frames):
  state=backend.state();tick=state['stamp']['source_ns']+10_000_000;started=time.monotonic_ns()
  if i%5==0:
   images={}
   for name in ('head','left_wrist','right_wrist'):
    renderer.update_scene(backend.data,camera=name);images[name]=renderer.render().tolist()
   proc.stdin.write(json.dumps({'state':state,'images':images,'instruction':'Hold both robot tools at their initial positions in free space.'})+'\n');proc.stdin.flush();result=response(30)
   age=time.monotonic_ns()-started
   if age>executor.limits['max_age_ns']:raise TimeoutError('observation expired during rendering/inference')
   scheduler.install(result['actions'],state,tick,semantics=SEMANTICS);latency.append(result['inference_latency_ns']/1e6)
  scheduler.submit_due(state,tick);backend.step(50);completed+=1
  end_to_end.append((time.monotonic_ns()-started)/1e6);collisions+=len(backend.contacts())
  errors.append(max(float(np.linalg.norm(backend.pose_matrix(s)[:3,3]-targets[s])) for s in targets))
  if collisions:raise ValueError('collision')
except Exception as e:violations.append(str(e));backend.hold()
finally:
 proc.terminate()
 try:proc.wait(timeout=10)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
 renderer.close();selector.close();log.close()
report={'status':'PASS_MODEL' if completed==a.frames and not violations else 'FAIL','model':a.model,'task':'free_space_hold_v1','success_rate':float(completed==a.frames and not violations and max(errors,default=math.inf)<.02),'completed_frames':completed,'collision_contacts':collisions,'safety_violations':violations,'inference_latency_ms':latency,'end_to_end_latency_ms':end_to_end,'target_action_frequency_hz':10,'wall_action_frequency_hz':completed/((time.monotonic_ns()-began)/1e9),'max_tool_displacement_m':max(errors,default=None),'training_resources':'NOT_RUN','dataset_profile':'3 RGB + joint/width; no depth/tactile','camera_calibration':'virtual renderer only','initial_state':'DualFR3.HOME','hardware':'NOT_RUN'}
(a.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(0 if report['status']=='PASS_MODEL' else 1)
