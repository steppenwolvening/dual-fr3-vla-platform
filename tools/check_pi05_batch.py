#!/usr/bin/env python3
"""Real native PI05 training dataset factory; CPU only, no checkpoint/tokenizer downloads."""
import os,sys,json,argparse,hashlib,importlib.metadata
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
for k in ('HF_HUB_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from fr3_platform.exporter import PROFILE
p=argparse.ArgumentParser();p.add_argument('splits',type=Path);a=p.parse_args()
import torch,numpy as np
from torch.utils.data import DataLoader
from lerobot.configs import FeatureType,PolicyFeature
from lerobot.configs.default import DatasetConfig
from lerobot.configs.train import TrainPipelineConfig
from lerobot.datasets.factory import make_dataset
from lerobot.policies.pi05.configuration_pi05 import PI05Config
cameras=['head','left_wrist','right_wrist']
policy=PI05Config(device='cpu',chunk_size=50,n_action_steps=5,input_features={
 'observation.state':PolicyFeature(type=FeatureType.STATE,shape=(16,)),
 **{'observation.images.'+c:PolicyFeature(type=FeatureType.VISUAL,shape=(3,8,8)) for c in cameras}},
 output_features={'action':PolicyFeature(type=FeatureType.ACTION,shape=(16,))},action_feature_names=PROFILE)
records=[];stats_hashes=[]
for split in ('train','validation','test'):
 path=(a.splits/split).resolve();mapping=json.loads((path/'canonical_mapping.json').read_text())
 assert mapping['fields']==PROFILE and mapping['split']==split and mapping['label']=='sent'
 cfg=TrainPipelineConfig(dataset=DatasetConfig(repo_id='local/dual-fr3-'+split,root=str(path),use_imagenet_stats=False),policy=policy,num_workers=0,batch_size=2)
 dataset=make_dataset(cfg)
 batch=next(iter(DataLoader(dataset,batch_size=2,num_workers=0,shuffle=False)))
 assert batch['action'].shape==(2,50,16) and batch['action'].dtype==torch.float32
 assert batch['observation.state'].shape==(2,16)
 assert batch['action_is_pad'].shape==(2,50) and batch['action_is_pad'].dtype==torch.bool
 assert not batch['action_is_pad'][0,:20].any() and batch['action_is_pad'][0,20:].all()
 for c in cameras:
  im=batch['observation.images.'+c];assert im.shape==(2,3,8,8) and im.dtype==torch.float32 and (im>=0).all() and (im<=1).all()
 assert len(batch['task'])==2 and all(batch['task'])
 for key in ('action','observation.state'):
  assert {'q01','q99'}<=set(dataset.meta.stats[key]),'missing train quantiles'
  assert torch.isfinite(batch[key]).all()
 stats_hashes.append(hashlib.sha256((path/'training_statistics.json').read_bytes()).hexdigest())
 records.append({'split':split,'frames':len(dataset),'tensor_shapes':{k:list(v.shape) for k,v in batch.items() if isinstance(v,torch.Tensor)},'dtypes':{k:str(v.dtype) for k,v in batch.items() if isinstance(v,torch.Tensor)},'action_padding_true_per_sample':batch['action_is_pad'].sum(1).tolist(),'task':batch['task'][0]})
assert len(set(stats_hashes))==1
report={'status':'PASS_OFFLINE','runtime':'native LeRobot PI05 training factory + torch DataLoader','versions':{k:importlib.metadata.version(k) for k in ('lerobot','torch','transformers','datasets')},'internal_max_action_dim':policy.max_action_dim,'chunk_size':50,'n_action_steps':5,'normalization':'train q01/q99 available; full processor/tokenizer NOT_RUN','model_forward':'NOT_RUN','training':'NOT_RUN','records':records,'stats_sha256':stats_hashes[0]}
(root/'validation/phase2/pi05_batch.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
