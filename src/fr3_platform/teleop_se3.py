"""Dual controller SE(3) mapping. Synthetic/replayed WebXR-format input, no hardware control."""
import numpy as np
from scipy.spatial.transform import Rotation
from .contracts import SIDES,require

class DualPoseMapper:
    def __init__(self,robot_from_tracking,origin,gain=1.,timeout_ns=100_000_000):
        r=np.asarray(robot_from_tracking,dtype=float)
        require(r.shape==(3,3) and np.isfinite(r).all() and np.allclose(r@r.T,np.eye(3)) and abs(np.linalg.det(r)-1)<1e-6,'explicit proper frame rotation')
        require(origin and origin!='UNCONFIGURED' and 0<gain<=2,'origin/gain')
        self.rotation=r;self.origin=origin;self.gain=gain;self.timeout_ns=timeout_ns
        self.anchors={};self.previous={};self.last_seq=-1;self.last_time=-1

    def update(self,frame,current_poses,now_ns):
        require(frame['schema']=='fr3.vr-pose/1','VR pose schema')
        require(frame['sequence']>self.last_seq and frame['common_time_ns']>self.last_time,'VR ordering')
        self.last_seq=frame['sequence'];self.last_time=frame['common_time_ns']
        targets={s:current_poses[s].copy() for s in SIDES};widths={};active=[];reasons={}
        fresh=0<=now_ns-frame['common_time_ns']<=self.timeout_ns and frame['tracking_origin']==self.origin
        for s in SIDES:
            hand=frame['hands'][s]
            if not fresh or not hand['tracking'] or not hand['deadman']:
                self.anchors.pop(s,None);self.previous.pop(s,None);reasons[s]='stale/origin/tracking/deadman';continue
            pose=np.asarray(hand['world_from_grip'],dtype=float)
            require(pose.shape==(4,4) and np.isfinite(pose).all() and np.allclose(pose[3],[0,0,0,1]),'VR pose matrix')
            require(np.allclose(pose[:3,:3]@pose[:3,:3].T,np.eye(3),atol=1e-6) and abs(np.linalg.det(pose[:3,:3])-1)<1e-6,'VR proper rotation')
            previous=self.previous.get(s)
            if previous is not None:
                jump=np.linalg.norm(pose[:3,3]-previous[:3,3]);angle=Rotation.from_matrix(pose[:3,:3]@previous[:3,:3].T).magnitude()
                if jump>.1 or angle>.5:
                    self.anchors.pop(s,None);self.previous.pop(s,None);reasons[s]='pose jump';continue
            self.previous[s]=pose.copy()
            if s not in self.anchors or hand.get('clutch') or hand.get('recenter'):
                self.anchors[s]=(pose.copy(),current_poses[s].copy())
            vr0,robot0=self.anchors[s]
            target=robot0.copy();target[:3,3]+=self.gain*self.rotation@(pose[:3,3]-vr0[:3,3])
            target[:3,:3]=self.rotation@(pose[:3,:3]@vr0[:3,:3].T)@self.rotation.T@robot0[:3,:3]
            width=hand['opening_width_m'];require(np.isfinite(width) and 0<=width<=.08,'explicit gripper width; no guessed button mapping')
            targets[s]=target;widths[s]=float(width);active.append(s)
        return {'targets':targets,'opening_width_m':widths,'active':active,'release_reasons':reasons,'latency_ns':now_ns-frame['common_time_ns']}
