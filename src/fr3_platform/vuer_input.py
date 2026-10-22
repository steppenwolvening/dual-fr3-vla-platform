"""Vuer/OpenTeleVision-family controller event adapter, never a hardware command."""
from .contracts import require,vector

def controller_frame(value,*,sequence,received_ns,origin,buttons):
 require(origin and origin!='UNCONFIGURED','tracking origin calibration required')
 require(set(buttons)=={'deadman','clutch','recenter','gripper'},'explicit button mapping required')
 hands={}
 for side in ('left','right'):
  matrix=value.get(side);state=value.get(side+'State',{})
  tracking=matrix is not None and bool(state)
  if tracking:
   vector(matrix,16,'WebGL column-major grip matrix')
   # Vuer documents WebGL column-major storage. Never guess transpose from data.
   pose=[[matrix[c*4+r] for c in range(4)] for r in range(4)]
   require(all(k in state for k in buttons.values()),'configured controller buttons missing')
   grip=state[buttons['gripper']];require(isinstance(grip,(int,float)) and 0<=grip<=1,'grip analog range')
  else:pose=[[float(i==j) for j in range(4)] for i in range(4)];grip=0.
  hands[side]={'tracking':tracking,'deadman':tracking and state[buttons['deadman']] is True,'clutch':tracking and state[buttons['clutch']] is True,'recenter':tracking and state[buttons['recenter']] is True,'world_from_grip':pose,'opening_width_m':.08*(1-grip)}
 return {'schema':'fr3.vr-pose/1','sequence':sequence,'common_time_ns':received_ns,'tracking_origin':origin,'hands':hands,'clock_quality':'host_receive_only; device age and transport latency unknown','raw_controller_event':value}
