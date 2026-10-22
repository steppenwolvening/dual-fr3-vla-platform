"""ROS 2 Jazzy JSON envelope bridge to MuJoCo ONLY; never loads a Franka driver."""
import json,time,sys
sys.path.append("/usr/lib/python3/dist-packages") # ROS system dependencies, process-local fallback only
from .contracts import RobotCommand
from .control import OfflineExecutor


def main():
 import rclpy
 from rclpy.node import Node
 from std_msgs.msg import String
 from .mujoco_backend import DualFR3
 class Bridge(Node):
  def __init__(self):
   super().__init__('dual_fr3_sim_bridge',namespace='/fr3_offline')
   self.backend=DualFR3();self.command_executor=OfflineExecutor(self.backend,self.backend.limits())
   self.state=None;self.failed=False
   self.pub=self.create_publisher(String,'state',10);self.receipt=self.create_publisher(String,'receipt',10)
   self.create_subscription(String,'command',self.command,10);self.create_timer(.05,self.tick)
  def tick(self):
   now=time.monotonic_ns();old=self.command_executor.owner;self.command_executor.watchdog(now)
   if old and not self.command_executor.owner:self.backend.hold()
   if self.failed:self.backend.hold()
   else:
    try:self.backend.step(25)
    except Exception:self.failed=True;self.command_executor.watchdog(now,estop=True);self.backend.hold()
   self.state=self.backend.state();self.state['stamp'].update(source_ns=now,received_ns=now,clock='host_monotonic',receive_clock='host_monotonic')
   if self.backend.contacts():self.failed=True;self.command_executor.watchdog(now,estop=True);self.backend.hold()
   self.pub.publish(String(data=json.dumps(self.state)))
  def command(self,msg):
   try:
    envelope=json.loads(msg.data);cmd=RobotCommand(envelope['command']).validate().payload
    now=time.monotonic_ns()
    if self.failed:raise ValueError('simulation fault latched')
    self.command_executor.acquire(cmd['owner'],now,envelope['lease_ns'])
    result=self.command_executor.submit(cmd,self.state,now)
    result={'status':'submitted_to_simulation','command_id':cmd['command_id'],'semantics':result['interface_semantics']}
   except Exception as e:result={'status':'rejected','reason':str(e)}
   self.receipt.publish(String(data=json.dumps(result)))
 rclpy.init();node=Bridge()
 try:rclpy.spin(node)
 finally:node.backend.hold();node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
