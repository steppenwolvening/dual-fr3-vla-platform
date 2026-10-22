"""Offline translation-only clutch mapper. Live Quest and rotation/IK remain BLOCKED."""
import math
from .contracts import require, vector, number

class OfflineVRMapper:
    def __init__(self, rotation, gain, max_jump_m, origin):
        require(len(rotation)==3, '3x3 rotation')
        for row in rotation: vector(row,3,'rotation row')
        for i in range(3):
            for j in range(3):
                require(abs(sum(rotation[i][k]*rotation[j][k] for k in range(3))-(1 if i==j else 0)) < 1e-6, 'rotation not orthonormal')
        r=rotation
        det=r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0])
        require(abs(det-1)<1e-6, 'reflection not allowed')
        require(number(gain) and gain>0 and number(max_jump_m) and max_jump_m>0, 'offline gains')
        require(origin and origin!='UNCONFIGURED', 'tracking origin')
        self.rotation,self.gain,self.max_jump,self.origin=rotation,gain,max_jump_m,origin
        self.previous=None
        self.last_seq=-1
        self.last_ns=-1

    def sample(self, position_m, *, sequence, source_ns, now_ns, origin, tracking, deadman, clutch=False, recenter=False):
        vector(position_m,3,'VR position')
        require(type(sequence) is int and type(source_ns) is int and type(now_ns) is int, 'VR time/sequence')
        if not tracking or not deadman or origin!=self.origin or not 0<=now_ns-source_ns<=100_000_000:
            self.previous=None
            return {'status':'REVOKE_AUTHORITY','reason':'tracking/deadman/origin/stale'}
        require(sequence>self.last_seq and source_ns>self.last_ns,'VR out of order')
        self.last_seq,self.last_ns=sequence,source_ns
        if clutch or recenter or self.previous is None:
            self.previous=list(position_m)
            return {'status':'REANCHORED','translation_m':[0.,0.,0.]}
        delta=[x-y for x,y in zip(position_m,self.previous)]
        self.previous=list(position_m)
        if math.sqrt(sum(x*x for x in delta))>self.max_jump:
            self.previous=None
            return {'status':'REVOKE_AUTHORITY','reason':'jump'}
        return {'status':'OFFLINE_TARGET_DELTA','translation_m':[self.gain*sum(r[i]*delta[i] for i in range(3)) for r in self.rotation],
                'rotation':'BLOCKED_REQUIRES_VERIFIED_POSE_CHAIN_AND_IK'}
