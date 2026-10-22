"""Lazy real runtime adapters. Model execution requires an approved local checkpoint.

NOT model-validated yet: see validation gates. No download or hardware code here.
"""
import os,json,hashlib
from pathlib import Path
from .contracts import require
from .exporter import PROFILE
from .vla import SEMANTICS,physical_state

def verify_profile(checkpoint,profile,model):
 checkpoint=Path(checkpoint).resolve();p=json.loads(Path(profile).read_text())
 require(checkpoint.is_dir(),'local checkpoint required')
 require(p['model']==model and p['robot']=='dual_fr3_franka_hand' and p['physical_fields']==PROFILE and p['output_semantics']==SEMANTICS,'checkpoint embodiment/units not verified')
 require(p.get('training_split_manifest_sha256') and p.get('normalization_sha256'),'trained data/stats identity required')
 require(bool(p.get('files')),'checkpoint file digests required')
 actual={str(f.relative_to(checkpoint)) for f in checkpoint.rglob('*') if f.is_file()}
 require(actual==set(p['files']),'every checkpoint/config/processor file must have a reviewed digest')
 for name,digest in p['files'].items():
  f=(checkpoint/name).resolve();require(f.is_relative_to(checkpoint) and f.is_file(),'checkpoint file path')
  h=hashlib.sha256()
  with f.open('rb') as stream:
   for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
  require(h.hexdigest()==digest,'checkpoint digest mismatch')
 for key in ('HF_HUB_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[key]='1'
 return checkpoint,p

class NativePI05:
 def __init__(self,checkpoint,profile,device='cuda'):
  checkpoint,metadata=verify_profile(checkpoint,profile,'pi05_native')
  require('model.safetensors' in metadata['files'],'PI05 weight digest required')
  import torch
  from safetensors.torch import load_file
  from lerobot.policies.pi05.configuration_pi05 import PI05Config
  from lerobot.policies.pi05.modeling_pi05 import PI05Policy
  from lerobot.policies.factory import make_pre_post_processors
  cfg=PI05Config.from_pretrained(str(checkpoint),local_files_only=True);cfg.device=device
  require(tuple(cfg.output_features['action'].shape)==(16,) and not cfg.use_relative_actions,'PI05 trained physical profile incompatible')
  require(set(cfg.image_features)=={'observation.images.'+c for c in ('head','left_wrist','right_wrist')},'PI05 camera mapping incompatible')
  # The audited upstream from_pretrained catches load errors and returns a model.
  # Use its real key migration machinery, but strict loading with no error swallowing.
  self.policy=PI05Policy(cfg)
  weights=load_file(str(checkpoint/'model.safetensors'))
  weights=self.policy._fix_pytorch_state_dict(weights,cfg)
  weights={k if k.startswith('model.') else 'model.'+k:v for k,v in weights.items()}
  self.policy.load_state_dict(self.policy._prepare_pretrained_state_dict(weights),strict=True)
  self.policy.eval();self.torch=torch
  self.pre,self.post=make_pre_post_processors(cfg,pretrained_path=str(checkpoint),preprocessor_overrides={'device_processor':{'device':device}})
 def predict(self,state,images,instruction):
  torch=self.torch
  obs={'observation.state':torch.tensor([physical_state(state)],dtype=torch.float32),'task':[instruction]}
  for name in ('head','left_wrist','right_wrist'):
   im=torch.as_tensor(images[name]);require(im.ndim==3 and im.shape[-1]==3 and im.dtype==torch.uint8,'RGB HWC uint8 required')
   obs['observation.images.'+name]=im.permute(2,0,1).float().div(255).unsqueeze(0)
  with torch.inference_mode():out=self.post(self.policy.predict_action_chunk(self.pre(obs)))
  require(out.ndim==3 and out.shape[0]==1 and out.shape[-1]==16,'PI05 external chunk dimensions')
  return out[0].float().cpu().tolist()

class LingBotV2:
 def __init__(self,checkpoint,profile,robot_config,norm_stats):
  checkpoint,metadata=verify_profile(checkpoint,profile,'lingbot_vla_v2')
  require(any(x.endswith('.safetensors') for x in metadata['files']),'LingBot weight shards required')
  require(hashlib.sha256(Path(norm_stats).read_bytes()).hexdigest()==metadata['normalization_sha256'],'LingBot stats mismatch')
  # Full upstream inference expects hf_ckpt under its training run tree, including
  # lingbotvla_cli.yaml three parents above; retain that layout, no guessed rewrite.
  require((checkpoint.parent.parent.parent/'lingbotvla_cli.yaml').is_file(),'LingBot training run configuration missing')
  from deploy.lingbot_vla_v2_policy import LingbotVLAv2Server
  from lingbotvla.data.vla_data.utils import FeatureTransform
  self.server=LingbotVLAv2Server(path_to_pi_model=str(checkpoint),robot_norm_path=str(norm_stats),use_length=5,chunk_ret=True,use_bf16=False,use_fp32=True,use_compile=False)
  self.server.vla.feature_transform=FeatureTransform(str(robot_config),self.server.data_config,self.server.config,self.server.processor,chunk_size=self.server.config.chunk_size,norm_stats_path=str(norm_stats))
  self.server.action_key=self.server.vla.feature_transform.org_features['actions']
  require(self.server.action_key==['action'],'LingBot inverse mapping must reconstruct one physical action vector')
 def predict(self,state,images,instruction):
  import numpy as np
  obs={'observation.state':np.asarray(physical_state(state),dtype=np.float32),'task':instruction}
  for name in ('head','left_wrist','right_wrist'):
   im=np.asarray(images[name]);require(im.ndim==3 and im.shape[-1]==3 and im.dtype==np.uint8,'RGB HWC uint8 required');obs['observation.images.'+name]=im
  out=self.server.infer(obs,center_crop=False)['action']
  require(out.ndim==2 and out.shape[-1]==16,'LingBot denormalized/inverse-mapped chunk dimensions')
  return out.tolist()
