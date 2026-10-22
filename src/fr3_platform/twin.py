"""File/pipe JSONL state protocol for isolated processes; no command return channel."""
import json
from .contracts import RobotState, require, SIDES
from .data import DatasetReader, validate


def state_packets(root, mode='REPLAY'):
    require(mode in ('REPLAY','SHADOW','SIMULATION'),'twin mode')
    require(mode=='REPLAY','file publisher only supports REPLAY; live SHADOW/simulation arbitration not implemented')
    require(validate(root)['ok'],'invalid canonical episode')
    r=DatasetReader(root)
    for e in r:
        if e['kind']=='state':
            t,u=r.common_time(e)
            yield {'protocol':'fr3.twin/1','mode':mode,'authority':'recorded_state','source_event_id':e['id'],
                   'common_time_ns':t,'clock_uncertainty_ns':u,'state':e['payload']}


def compare_packets(a,b):
    require(a['source_event_id']==b['source_event_id'] and a['common_time_ns']==b['common_time_ns'],'cannot compare different source instants')
    for packet in (a,b):RobotState(packet['state']).validate()
    errors=[]
    for s in SIDES:
        av,bv=a['state']['arms'][s]['position']['value'],b['state']['arms'][s]['position']['value']
        require(av is not None and bv is not None,'missing state')
        errors.extend(abs(x-y) for x,y in zip(av,bv))
    return {'source_event_id':a['source_event_id'],'max_joint_error_rad':max(errors),
            'meaning':'joint agreement only, not contact/dynamics equivalence'}


class MuJoCoReplay:
    """Actual MuJoCo file loading and named qpos/qvel mapping, requires reviewed model manifest.

    This is a kinematic replay consumer. No simulation command dispatch or real robot connection.
    """
    def __init__(self, model_path, manifest):
        require(manifest.get('hardware')=='Dual FR3 + Franka Gripper','model embodiment')
        require(manifest.get('review_status')=='VERIFIED_FOR_ASSEMBLY','model applicability not verified')
        for key in ('calibration_version','model_sha256','gripper_width_mapping'):
            require(manifest.get(key) not in (None,'UNCONFIGURED'),f'missing {key}')
        import hashlib
        from pathlib import Path
        require(hashlib.sha256(Path(model_path).read_bytes()).hexdigest()==manifest['model_sha256'],'model digest')
        import mujoco
        self.mj=mujoco
        self.model=mujoco.MjModel.from_xml_path(str(model_path))
        self.data=mujoco.MjData(self.model)
        self.manifest=manifest
        self.map={}
        for side in SIDES:
            names=manifest['joint_names'][side]
            require(len(names)==7 and len(set(names))==7,'seven distinct joints')
            self.map[side]=[self.model.joint(name).id for name in names]
        ids=sum(self.map.values(),[])
        require(len(set(ids))==14,'left/right joints overlap')
        for jid in ids:require(self.model.jnt_type[jid]==mujoco.mjtJoint.mjJNT_HINGE,'arm joint must be hinge')

    def apply(self, packet):
        require(packet['mode'] in ('REPLAY','SHADOW'),'kinematic consumer cannot advance simulation')
        RobotState(packet['state']).validate()
        for side in SIDES:
            a=packet['state']['arms'][side]
            require(a['position']['value'] is not None,'joint state missing')
            for i,(jid,q) in enumerate(zip(self.map[side],a['position']['value'])):
                if self.model.jnt_limited[jid]:require(self.model.jnt_range[jid,0]<=q<=self.model.jnt_range[jid,1],'model joint limit')
                self.data.qpos[self.model.jnt_qposadr[jid]]=q
                self.data.qvel[self.model.jnt_dofadr[jid]]=a['velocity']['value'][i] if a['velocity']['value'] is not None else 0
            width=a['gripper']['value']
            require(width is not None,'gripper width missing')
            for item in self.manifest['gripper_width_mapping'][side]:
                jid=self.model.joint(item['joint']).id
                require(self.model.jnt_type[jid]==self.mj.mjtJoint.mjJNT_SLIDE,'gripper must be explicit slide mapping')
                q=width*item['scale']+item['offset_m']
                require(self.model.jnt_range[jid,0]<=q<=self.model.jnt_range[jid,1],'gripper model limit')
                self.data.qpos[self.model.jnt_qposadr[jid]]=q
                self.data.qvel[self.model.jnt_dofadr[jid]]=0
        self.mj.mj_forward(self.model,self.data)
        return {side:[float(self.data.qpos[self.model.jnt_qposadr[j]]) for j in self.map[side]] for side in SIDES}
