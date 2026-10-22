#!/usr/bin/env python3
"""Compile official URDF with MuJoCo, then add explicit simulation-only actuators/sites."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import mujoco
root=Path(__file__).resolve().parents[1];out=root/'assets/fr3_reference'
model=mujoco.MjModel.from_xml_path(str(out/'dual_fr3.urdf'))
mujoco.mj_saveLastXML(str(out/'dual_fr3.xml'),model)
tree=ET.parse(out/'dual_fr3.xml');r=tree.getroot()
option=r.find('option')
if option is None:option=ET.SubElement(r,'option')
option.set('timestep','0.002');option.set('integrator','implicitfast')
act=ET.SubElement(r,'actuator');eq=ET.SubElement(r,'equality')
for side in ('left','right'):
 for i in range(1,8):
  name=f'{side}_fr3_joint{i}'
  joint=r.find(f".//joint[@name='{name}']");joint.set('armature','0.05');joint.set('damping','1')
  ET.SubElement(act,'position',name=name+'_position',joint=name,kp='400',kv='40',ctrlrange=joint.attrib['range'],forcerange='-87 87' if i<=4 else '-12 12')
 for i in (1,2):
  name=f'{side}_fr3_finger_joint{i}'
  joint=r.find(f".//joint[@name='{name}']");joint.set('armature','0.01')
  ET.SubElement(act,'position',name=name+'_position',joint=name,kp='200',kv='5',ctrlrange='0 0.04',forcerange='-100 100')
 ET.SubElement(eq,'joint',joint1=f'{side}_fr3_finger_joint2',joint2=f'{side}_fr3_finger_joint1',polycoef='0 1 0 0 0')
 tcp=r.find(f".//body[@name='{side}_fr3_hand_tcp']");ET.SubElement(tcp,'site',name=f'{side}_tcp',size='0.005',rgba='1 0 0 1')
for body in r.findall('.//body'):
 original=model.body(body.attrib['name'])
 body.set('pos',' '.join(format(float(x),'.17g') for x in original.pos))
 body.set('quat',' '.join(format(float(x),'.17g') for x in original.quat))
 if body.find('inertial') is not None:body.set('gravcomp','1')
ET.indent(r);tree.write(out/'dual_fr3.xml',encoding='unicode')
model=mujoco.MjModel.from_xml_path(str(out/'dual_fr3.xml'));data=mujoco.MjData(model)
for s in ('left','right'):
 for i,q in enumerate([0,-0.5,0,-2,0,1.5,0.785398],1):data.qpos[model.joint(f'{s}_fr3_joint{i}').qposadr[0]]=q
 for i in (1,2):data.qpos[model.joint(f'{s}_fr3_finger_joint{i}').qposadr[0]]=.02
for i in range(model.nu):data.ctrl[i]=data.qpos[model.jnt_qposadr[model.actuator_trnid[i,0]]]
mujoco.mj_forward(model,data)
print(json.dumps({'nq':model.nq,'nv':model.nv,'nu':model.nu,'bodies':model.nbody,'geoms':model.ngeom,'contacts':data.ncon,'model':'official FR3 + Franka Hand; virtual bases; simulation-only actuators'}))
for i in range(data.ncon):
 c=data.contact[i];print('contact',model.geom(c.geom1).name,model.geom(c.geom2).name,float(c.dist))
