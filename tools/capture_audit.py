"""Bounded read-only provenance collector. Explicit --source-root, never searches Home."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--source-root',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
root=a.source_root
specs={
 'franka_description':('robotics/vendor/franka_official/repos/franka_description',['package.xml','LICENSE','robots/fr3/kinematics.yaml','robots/fr3/joint_limits.yaml']),
 'franka_ros2':('robotics/vendor/franka_official/repos/franka_ros2',['dependency.repos','franka_bringup/test/test_fr3_duo_interfaces.py','franka_bringup/urdf/fr3_duo.urdf.xacro']),
 'libfranka':('robotics/vendor/franka_official/repos/libfranka',['package.xml','LICENSE']),
 'IsaacLab':('robotics/repos/IsaacLab',['VERSION','pyproject.toml']),
 'lerobot':('Desktop/lerobot',['pyproject.toml','src/lerobot/datasets/lerobot_dataset.py','src/lerobot/scripts/lerobot_record.py']),
 'flexitac_sim_reference':('Desktop/flexitac_fr3_twin_dc2e1c6',['README.md','environment.yml','fr3_adapter/README.md'])}
report={'evidence':'FILE_VERIFIED','host':platform.node(),'interpreter':sys.executable,'python':platform.python_version(),'repos':{},'source_files':[]}
for name,(rel,files) in specs.items():
 repo=root/rel
 if not repo.is_dir():report['repos'][name]={'status':'MISSING','path':str(repo)};continue
 def git(*cmd):
  return subprocess.run(['git','--no-optional-locks','-C',str(repo),*cmd],capture_output=True,text=True,check=True).stdout.strip()
 remote=git('config','--get','remote.origin.url')
 if '@' in remote and not remote.startswith('git@'):remote='REDACTED_URL'
 report['repos'][name]={'path':str(repo),'url':remote,'commit':git('rev-parse','HEAD'),'tracked_status':git('status','--porcelain','--untracked-files=no'),'evidence':'FILE_VERIFIED'}
 for name2 in files:
  f=repo/name2
  if f.is_file():report['source_files'].append({'path':str(f),'size':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
report['environments']={}
for rel in ('miniforge3/envs/mujoco_sim','miniforge3/envs/lerobot','robotics/repos/IsaacLab/.venv'):
 packages={}
 for site in (root/rel).glob('lib/python*/site-packages'):
  for d in importlib.metadata.distributions(path=[str(site)]):
   name=d.metadata['Name'].lower().replace('_','-')
   if name in ('mujoco','mink','lerobot','numpy','torch','torchvision','torchaudio','isaacsim','isaaclab','pyrealsense2','vuer'):
    packages[name]=d.version
 report['environments'][str(root/rel)]={'evidence':'FILE_VERIFIED','metadata_only':True,'packages':packages}
hub=root/'.cache/huggingface/hub'
report['lingbot']={'evidence':'UNKNOWN','selected_checkpoint':'UNCONFIGURED','scope':'only named source roots and LingBot-named HF repo directories', 'hub_exists':hub.exists(), 'matching_repositories':[x.name for x in hub.iterdir() if 'lingbot' in x.name.lower()] if hub.is_dir() else []}
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'repos':len(report['repos']),'source_files':len(report['source_files']),'output':str(a.output)}))
