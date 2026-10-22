"""Model-independent physical action contract and bounded chunk scheduling.

Model-specific normalization lives in each runtime. Only denormalized absolute
joint targets (rad) + full finger opening widths (m) reach this boundary.
"""
import copy,math
from .contracts import RobotState,RobotCommand,JOINTS,SIDES,require,vector
from .exporter import PROFILE

SEMANTICS='absolute_joint_rad_left7_right7_opening_width_m_left_right'

def physical_state(state):
 RobotState(state).validate()
 require(all(state['arms'][s]['position']['value'] is not None and state['arms'][s]['gripper']['value'] is not None for s in SIDES),'model observation missing state/gripper')
 return sum([state['arms'][s]['position']['value'] for s in SIDES],[])+[state['arms'][s]['gripper']['value'] for s in SIDES]

def action_command(action,state,*,now_ns,sequence,clock,command_id):
 vector(action,16,'denormalized physical action')
 cmd={'command_id':command_id,'observation_id':state['state_id'],'owner':'vla','kind':'joint_position','side_order':list(SIDES),
      'stamp':{'source_ns':now_ns,'received_ns':now_ns,'sequence':sequence,'clock':clock,'receive_clock':clock},'arms':{}}
 for i,s in enumerate(SIDES):
  cmd['arms'][s]={'joint_names':JOINTS[s],'unit':'rad','target':list(action[i*7:i*7+7]),'gripper':{'quantity':'opening_width','unit':'m','target':action[14+i]}}
 return RobotCommand(cmd).validate().payload

class ChunkScheduler:
 """Drop expired chunks, zero-order hold at a declared rate, always use executor.

No implicit clamping, extrapolation, background thread or direct backend writes.
Replan within max_steps; source observation must be fresh when installing chunk.
"""
 def __init__(self,executor,period_ns=100_000_000,max_steps=5):
  require(type(period_ns)is int and period_ns>0 and type(max_steps)is int and 0<max_steps<=50,'chunk schedule')
  self.executor=executor;self.period=period_ns;self.max_steps=max_steps;self.chunk=None;self.sequence=0;self.last_index=-1
 def install(self,actions,observation,generated_ns,*,semantics):
  require(semantics==SEMANTICS,'model output semantics not verified')
  RobotState(observation).validate();require(0<=generated_ns-observation['stamp']['source_ns']<=self.executor.limits['max_age_ns'],'inference observation expired')
  require(0<len(actions)<=100,'bounded action horizon')
  for action in actions:vector(action,16,'physical chunk')
  self.chunk=copy.deepcopy(actions[:self.max_steps]);self.started=generated_ns;self.last_index=-1
 def submit_due(self,state,now_ns):
  if self.chunk is None:return None
  elapsed=now_ns-self.started;require(elapsed>=0,'clock moved backwards')
  index=elapsed//self.period
  if index>=len(self.chunk):self.chunk=None;self.executor.release('chunk exhausted');self.executor.sink.hold();return None
  if index==self.last_index:return None
  # Missed samples are dropped; never burst old commands to catch up.
  self.executor.acquire('vla',now_ns,min(self.period*2,1_000_000_000))
  command=action_command(self.chunk[index],state,now_ns=now_ns,sequence=self.sequence,clock=self.executor.clock,command_id=f'vla-{self.sequence}')
  try:result=self.executor.submit(command,state,now_ns)
  except Exception:
   self.chunk=None;self.executor.release('invalid model action');self.executor.sink.hold();raise
  self.sequence+=1;self.last_index=index;return result
