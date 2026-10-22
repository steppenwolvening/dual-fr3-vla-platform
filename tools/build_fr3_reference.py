#!/usr/bin/env python3
"""Expand pinned official FR3/Franka Hand; retain collision mesh geometry, never old hardware.

Run with ROS system Python for xacro, then compile with MuJoCo in a separate process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

p=argparse.ArgumentParser();p.add_argument('--franka-source',type=Path,required=True);p.add_argument('--ros-prefix',type=Path,default=Path('/opt/ros/jazzy'))
a=p.parse_args();root=Path(__file__).resolve().parents[1];source=a.franka_source.resolve();out=root/'assets/fr3_reference';out.mkdir(parents=True,exist_ok=True)
commit=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
assert commit=='02afaae282d4a8e10d7d2f781b23b3515c303ce5'
sys.path.insert(0,str(a.ros_prefix/'lib/python3.12/site-packages'))
import xacro
import xacro.substitution_args
# Isolated generator package resolution, no system overlay or source edits.
xacro.substitution_args._eval_find=lambda package: str(source) if package=='franka_description' else (_ for _ in ()).throw(ValueError(package))
robot=ET.Element('robot',name='dual_fr3_reference');ET.SubElement(robot,'link',name='world')
manifest={'schema':'fr3.reference-model/1','source_commit':commit,'url':'https://github.com/frankarobotics/franka_description','source_model':'fr3','license':'Apache-2.0','scope':'SIMULATION_REFERENCE_ONLY_NOT_LAB_CALIBRATION','hardware_assembly_verified':False,'world_bases':{},'joint_order':{},'limits':{},'frames':{},'assets':[]}
copied={}
for side,y in [('left',0.55),('right',-0.55)]:
 tree=ET.fromstring(xacro.process_file(str(source/'robots/fr3/fr3.urdf.xacro'),mappings={'arm_prefix':side,'hand':'true','with_sc':'false','gazebo':'false'}).toxml())
 for link in tree.findall('link'):
  if link.attrib['name']=='base':continue
  for visual in list(link.findall('visual')):link.remove(visual)
  for i,collision in enumerate(link.findall('collision')):
   collision.set('name',link.attrib['name']+f'_collision_{i}')
  for mesh in link.findall('.//mesh'):
   rel=mesh.attrib['filename'].removeprefix('package://franka_description/')
   src=source/rel;name=rel.replace('/','_');dst=out/'meshes'/name;dst.parent.mkdir(exist_ok=True)
   if name not in copied:
    shutil.copyfile(src,dst);copied[name]=True
    manifest['assets'].append({'path':'meshes/'+name,'source_relative_path':rel,'size_bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'purpose':'official FR3/Franka Hand collision geometry'})
   mesh.set('filename','meshes/'+name)
  robot.append(link)
 for joint in tree.findall('joint'):
  if joint.find('parent').attrib['link']=='base':
   joint.find('parent').set('link','world');joint.find('origin').set('xyz',f'0 {y} 0')
  robot.append(joint)
 manifest['world_bases'][side]={'xyz_m':[0,y,0],'rpy_rad':[0,0,0],'source':'deliberate virtual layout, not real calibration'}
 names=[f'{side}_fr3_joint{i}' for i in range(1,8)];manifest['joint_order'][side]=names
 manifest['limits'][side]={j.attrib['name']:dict(j.find('limit').attrib) for j in tree.findall('joint') if j.attrib['name'] in names}
 manifest['frames'][side]={'base':f'{side}_fr3_link0','flange':f'{side}_fr3_link8','hand':f'{side}_fr3_hand','tcp':f'{side}_fr3_hand_tcp','tcp_source':'official default 0.1034m, no sensor/pad compensation'}
mj=ET.SubElement(robot,'mujoco');ET.SubElement(mj,'compiler',discardvisual='true',fusestatic='false',balanceinertia='false',strippath='false')
ET.indent(robot);ET.ElementTree(robot).write(out/'dual_fr3.urdf',encoding='unicode')
for name in ('LICENSE','NOTICE'):shutil.copyfile(source/name,out/name)
# Capture parameter evidence required for independent FK and limit comparison, not the entire repo.
for name in ('kinematics.yaml','joint_limits.yaml','inertials.yaml','dynamics.yaml'):
 shutil.copyfile(source/'robots/fr3'/name,out/name)
(out/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'output':str(out),'meshes':len(copied),'mesh_bytes':sum(x['size_bytes'] for x in manifest['assets']),'source_commit':commit}))
