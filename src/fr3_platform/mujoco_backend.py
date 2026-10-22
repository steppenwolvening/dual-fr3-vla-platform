"""Official FR3/Franka Hand simulation reference. Never a hardware backend."""
from pathlib import Path
import json
import math
import numpy as np
import mujoco
from .contracts import JOINTS, SIDES, RobotState, RobotCommand, require

MODEL=Path(__file__).resolve().parents[2]/'assets/fr3_reference/dual_fr3.xml'
HOME=np.array([0.,-.5,0.,-2.,0.,1.5,math.pi/4])

class DualFR3:
    source='simulation'
    def __init__(self, model_path=MODEL, *, model=None):
        self.model=model if model is not None else mujoco.MjModel.from_xml_path(str(model_path));self.data=mujoco.MjData(self.model)
        self.model_path=Path(model_path)
        self.manifest=json.loads((self.model_path.parent/'provenance.json').read_text())
        self.joints={s:[self.model.joint(f'{s}_fr3_joint{i}').id for i in range(1,8)] for s in SIDES}
        self.fingers={s:[self.model.joint(f'{s}_fr3_finger_joint{i}').id for i in (1,2)] for s in SIDES}
        self.sequence=0
        for s in SIDES:
            self.data.qpos[[self.model.jnt_qposadr[j] for j in self.joints[s]]]=HOME
            self.data.qpos[[self.model.jnt_qposadr[j] for j in self.fingers[s]]]=.02
        self.hold();mujoco.mj_forward(self.model,self.data)

    def hold(self):
        for i in range(self.model.nu):self.data.ctrl[i]=self.data.qpos[self.model.jnt_qposadr[self.model.actuator_trnid[i,0]]]

    def pose_matrix(self, side):
        site=self.model.site(f'{side}_tcp').id
        t=np.eye(4);t[:3,:3]=self.data.site_xmat[site].reshape(3,3);t[:3,3]=self.data.site_xpos[site]
        return t

    def validate_q(self, q):
        q=np.asarray(q)
        require(q.shape==(self.model.nq,) and np.isfinite(q).all(),'simulation q dimension/nonfinite')
        for j in range(self.model.njnt):
            if self.model.jnt_limited[j]:
                value=q[self.model.jnt_qposadr[j]]
                require(self.model.jnt_range[j,0]-1e-10<=value<=self.model.jnt_range[j,1]+1e-10,'simulation joint limit')

    def set_state(self,q,qd=None):
        self.validate_q(q)
        velocity=np.zeros(self.model.nv) if qd is None else np.asarray(qd)
        require(velocity.shape==(self.model.nv,) and np.isfinite(velocity).all(),'velocity dimension')
        self.data.qpos[:]=q;self.data.qvel[:]=velocity;mujoco.mj_forward(self.model,self.data);self.hold()

    def contacts(self):
        return [{'geom1':self.model.geom(c.geom1).name,'geom2':self.model.geom(c.geom2).name,'distance_m':float(c.dist)} for c in self.data.contact[:self.data.ncon] if c.dist < -1e-6]

    def send(self,command):
        RobotCommand(command).validate();require(command['kind']=='joint_position','simulation backend requires IK joint targets')
        q=self.data.qpos.copy()
        for s in SIDES:
            for j,value in zip(self.joints[s],command['arms'][s]['target']):q[self.model.jnt_qposadr[j]]=value
            width=command['arms'][s]['gripper']['target'];require(0<=width<=.08,'opening width must be 0..0.08m in reference model')
            for j in self.fingers[s]:q[self.model.jnt_qposadr[j]]=width/2
        self.validate_q(q)
        probe=mujoco.MjData(self.model);probe.qpos[:]=q;mujoco.mj_forward(self.model,probe)
        require(not any(c.dist < -1e-5 for c in probe.contact[:probe.ncon]),'target penetrates collision geometry')
        for i in range(self.model.nu):self.data.ctrl[i]=q[self.model.jnt_qposadr[self.model.actuator_trnid[i,0]]]
        return {'meaning':'MuJoCo actuator target assigned, not measured or hardware-executed','simulation_time_s':float(self.data.time)}

    def step(self,steps=5):
        require(type(steps)is int and 0<steps<=1000,'bounded simulation steps')
        for _ in range(steps):mujoco.mj_step(self.model,self.data)
        require(np.isfinite(self.data.qpos).all(),'unstable simulation')
        return self.state()

    def state(self):
        seq=self.sequence;self.sequence+=1;t=1_000_000_000+round(self.data.time*1e9)
        stamp={'source_ns':t,'received_ns':t,'sequence':seq,'clock':'simulation','receive_clock':'simulation'}
        arms={}
        for s in SIDES:
            mat=self.pose_matrix(s);quat=np.zeros(4);mujoco.mju_mat2Quat(quat,mat[:3,:3].reshape(-1))
            pose={'position_m':mat[:3,3].tolist(),'quaternion_xyzw':[*quat[1:],quat[0]],'frame':'world','child_frame':f'{s}_tcp','provenance':'MuJoCo FK; official fr3 reference; virtual base layout'}
            arms[s]={'joint_names':JOINTS[s],'position':{'value':[float(self.data.qpos[self.model.jnt_qposadr[j]]) for j in self.joints[s]],'unit':'rad','status':'measured'},
                     'velocity':{'value':[float(self.data.qvel[self.model.jnt_dofadr[j]]) for j in self.joints[s]],'unit':'rad/s','status':'measured'},
                     'gripper':{'value':float(sum(self.data.qpos[self.model.jnt_qposadr[j]] for j in self.fingers[s])),'unit':'m','quantity':'opening_width','status':'measured'},
                     'eef':None,'tcp':pose,'valid_fields':['position','velocity','gripper','tcp']}
        return RobotState({'state_id':f'state-{seq}','stamp':stamp,'source':'simulation','arms':arms,'controller_status':'simulation_position_servos','safety_status':'simulation_only_no_hardware'}).validate().payload

    def limits(self):
        out={'source':'official FR3 joint limits; simulation-only fixed velocity bounds','max_age_ns':250_000_000,'min_period_s':.001}
        for s in SIDES:
            limits=self.manifest['limits'][s]
            out[s]={'lower':[float(limits[n]['lower']) for n in self.manifest['joint_order'][s]],'upper':[float(limits[n]['upper']) for n in self.manifest['joint_order'][s]],
                    'velocity':[float(limits[n]['velocity']) for n in self.manifest['joint_order'][s]],'gripper':{'min_m':0.,'max_m':.08,'speed_m_s':.4}}
        return out

class MinkIK:
    def __init__(self, backend):
        import mink
        self.mink=mink;self.backend=backend;self.config=mink.Configuration(backend.model,backend.data.qpos.copy())
        self.tasks={s:mink.FrameTask(f'{s}_tcp','site',position_cost=1.,orientation_cost=1.,lm_damping=1.) for s in SIDES}
        self.posture=mink.PostureTask(backend.model,cost=1e-4);self.posture.set_target(backend.data.qpos.copy())
        velocities={name:float(lim['velocity']) for s in SIDES for name,lim in backend.manifest['limits'][s].items()}
        for s in SIDES:
            for i in (1,2):velocities[f'{s}_fr3_finger_joint{i}']=.2
        groups={s:[g for g in range(backend.model.ngeom) if backend.model.geom(g).name.startswith(s+'_')] for s in SIDES}
        pairs=[(groups['left'],groups['right'])]
        # Non-neighbour self-collision pairs; MuJoCo still validates all target contacts.
        for s in SIDES:
            for i in range(5):
                one=[g for g in groups[s] if backend.model.geom(g).name.startswith(f'{s}_fr3_link{i}_')]
                other=[g for g in groups[s] if any(backend.model.geom(g).name.startswith(f'{s}_fr3_link{k}_') for k in range(i+3,8))]
                if one and other:pairs.append((one,other))
        self.limits=[mink.ConfigurationLimit(backend.model),mink.VelocityLimit(backend.model,velocities),mink.CollisionAvoidanceLimit(backend.model,pairs,minimum_distance_from_collisions=.005,collision_detection_distance=.03)]

    def solve(self,targets,iterations=120,dt=.01):
        require(0<iterations<=300 and 0<dt<=.05,'bounded IK solve')
        self.config.update(self.backend.data.qpos.copy());self.posture.set_target(self.backend.data.qpos.copy())
        for s,task in self.tasks.items():task.set_target(self.mink.SE3.from_matrix(targets.get(s,self.backend.pose_matrix(s))))
        for iteration in range(iterations):
            v=self.mink.solve_ik(self.config,[*self.tasks.values(),self.posture],dt,'daqp',limits=self.limits)
            self.config.integrate_inplace(v,dt)
            residuals={s:{'position_m':float(np.linalg.norm(task.compute_error(self.config)[:3])),'rotation_rad':float(np.linalg.norm(task.compute_error(self.config)[3:]))} for s,task in self.tasks.items()}
            if max(x['position_m'] for x in residuals.values())<1e-4 and max(x['rotation_rad'] for x in residuals.values())<1e-3:break
        q=self.config.q.copy();self.backend.validate_q(q)
        require(max(x['position_m'] for x in residuals.values())<1e-3 and max(x['rotation_rad'] for x in residuals.values())<5e-3,'IK residual exceeded acceptance thresholds')
        return q,{'iterations':iteration+1,'residuals':residuals}
