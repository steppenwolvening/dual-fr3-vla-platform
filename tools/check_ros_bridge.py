#!/usr/bin/env python3
"""Separate process ROS IPC smoke. Run with ROS_LOCALHOST_ONLY=1 and an isolated domain."""
import os,sys,time,json,subprocess,signal
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
assert os.environ.get('ROS_LOCALHOST_ONLY')=='1' and os.environ.get('ROS_DOMAIN_ID')=='173'
sys.path.append("/usr/lib/python3/dist-packages")
import rclpy
from std_msgs.msg import String
from fr3_platform.contracts import JOINTS
log=(root/'artifacts/ros-bridge.log').open('w')
env=dict(os.environ,PYTHONPATH=str(root/'src')+os.pathsep+os.environ.get('PYTHONPATH',''))
proc=subprocess.Popen([sys.executable,'-B','-m','fr3_platform.ros_bridge'],env=env,stdout=log,stderr=log,start_new_session=True)
rclpy.init();node=rclpy.create_node('offline_smoke_client',namespace='/fr3_offline');states=[];receipts=[]
node.create_subscription(String,'state',lambda m:states.append(json.loads(m.data)),10)
node.create_subscription(String,'receipt',lambda m:receipts.append(json.loads(m.data)),10)
pub=node.create_publisher(String,'command',10)
def wait(test,seconds=10):
 deadline=time.monotonic()+seconds
 while not test() and time.monotonic()<deadline:
  assert proc.poll() is None,'bridge process exited; see artifacts/ros-bridge.log'
  rclpy.spin_once(node,timeout_sec=.005)
 assert test(),'ROS deadline'
try:
 wait(lambda:len(states)>3 and pub.get_subscription_count()>0)
 state=states[-1];now=time.monotonic_ns()
 cmd={'command_id':'ros-smoke-0','observation_id':state['state_id'],'owner':'replay','kind':'joint_position','side_order':['left','right'],'stamp':{'source_ns':now,'received_ns':now,'sequence':0,'clock':'host_monotonic','receive_clock':'host_monotonic'},'arms':{s:{'joint_names':JOINTS[s],'target':state['arms'][s]['position']['value'],'unit':'rad','gripper':{'target':state['arms'][s]['gripper']['value'],'unit':'m','quantity':'opening_width'}} for s in JOINTS}}
 pub.publish(String(data=json.dumps({'command':cmd,'lease_ns':200_000_000})));wait(lambda:bool(receipts))
 assert receipts[-1]['status']=='submitted_to_simulation',receipts[-1]
 count=len(states);wait(lambda:len(states)>count)
 state=states[-1];now=time.monotonic_ns();cmd['observation_id']=state['state_id']
 cmd['stamp'].update(source_ns=now,received_ns=now,sequence=1)
 cmd['command_id']='invalid';cmd['arms']['left']['target'][0]=99
 pub.publish(String(data=json.dumps({'command':cmd,'lease_ns':200_000_000})));wait(lambda:len(receipts)>1)
 assert receipts[-1]['status']=='rejected' and receipts[-1]['reason']=='position/velocity limit',receipts[-1]
 report={'status':'PASS_OFFLINE','transport':'ROS2 Jazzy DDS localhost; separate process; actual MuJoCo sink','domain':173,'state_messages':len(states),'receipts':receipts,'hardware':'NOT_RUN','driver_loaded':False}
 (root/'validation/phase2/ros_bridge.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
 if proc.poll() is None:os.killpg(proc.pid,signal.SIGINT)
 try:proc.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 log.close();node.destroy_node();rclpy.shutdown()
