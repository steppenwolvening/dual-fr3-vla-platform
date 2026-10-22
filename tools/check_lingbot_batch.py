#!/usr/bin/env python3
"""Execute pinned upstream VLADataset, FeatureTransform and padding, no tokenizer/model.

Leaf package imports deliberately avoid upstream data/__init__.py's unrelated full
training/distributed imports. No dataset, transforms, normalization or tensors are
mocked. Full tokenizer/collator/model runtime is a separate NOT_RUN gate.
"""
import os,sys,json,argparse,hashlib,types,copy,importlib.metadata
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('splits',type=Path);p.add_argument('--source',type=Path,default=root/'.deps/lingbot-audit');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for k in ('HF_HUB_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
source=a.source.resolve();audit=json.loads((source/'audit.json').read_text())
assert audit['commit']=='be969b8fd117fb70550c5d4bf4bc328211b5b1b6'
for entry in audit['files']:assert hashlib.sha256((source/entry['path']).read_bytes()).hexdigest()==entry['sha256']
sys.path.insert(0,str(source))
import lingbotvla
for name,relative in [('lingbotvla.data','lingbotvla/data'),('lingbotvla.data.vla_data','lingbotvla/data/vla_data')]:
 package=types.ModuleType(name);package.__path__=[str(source/relative)];sys.modules[name]=package
from lingbotvla.data.vla_data.base_dataset import VLADataset
from lingbotvla.data.vla_data.utils import FeatureTransform
from lingbotvla.data.vla_data.transform import prepare_state,prepare_action
import torch,numpy as np,yaml
from torch.utils.data import DataLoader
from types import SimpleNamespace
joints={'arm.position':14,'end.position':14,'effector.position':2,'waist.position':4,'head.position':2,'base.position':3,'hand.position':12}
data_cfg=SimpleNamespace(joints=[repr({k:v}) for k,v in joints.items()],cameras=['camera_top','camera_wrist_left','camera_wrist_right'],norm_type=[repr({k:'meanstd'}) for k in joints])
model_cfg=SimpleNamespace(max_state_dim=55,max_action_dim=55)
a.output.mkdir(parents=True,exist_ok=False)
robot_cfg=yaml.safe_load((root/'configs/vla/lingbot_dual_fr3.yaml').read_text())
robot_cfg['norm_stats']=str((a.output/'normalization.json').resolve())
(a.output/'dual_fr3.yaml').write_text(yaml.safe_dump(robot_cfg,sort_keys=False))
train=VLADataset(repo_id=str((a.splits/'train').resolve()),data_name='dual_fr3',dataset_config=data_cfg,robot_config_root=str(a.output),config=model_cfg,do_nomalize=False,return_item=True,chunk_size=50)
values={k:[] for k in train.feature_transform.states+train.feature_transform.actions}
for i in range(len(train)):
 item=train[i]
 for k in values:
  val=item[k]
  if k.startswith('action.'):val=val[~item['action_is_pad']]
  else:val=val[None]
  values[k].append(val.numpy())
stats={}
for k,parts in values.items():
 x=np.concatenate(parts,axis=0);stats[k]={name:getattr(x,name)(axis=0).tolist() for name in ('mean','std','min','max')};stats[k]['count']=len(x)
trainmap=json.loads((a.splits/'train/canonical_mapping.json').read_text())
record={'norm_stats':stats,'fit_split':'train','source_episode_ids':trainmap['source_episode_ids'],'fit_policy':'state once/frame; relative arm action on valid chunk entries only; gripper absolute meters','runtime_source_commit':audit['commit']}
(a.output/'normalization.json').write_text(json.dumps(record,indent=2)+'\n');before=(a.output/'normalization.json').read_bytes()
reports=[]
for split in ('train','validation','test'):
 mapping=json.loads((a.splits/split/'canonical_mapping.json').read_text())
 if split!='train':assert not set(mapping['source_episode_ids'])&set(record['source_episode_ids'])
 ds=VLADataset(repo_id=str((a.splits/split).resolve()),data_name='dual_fr3',dataset_config=data_cfg,robot_config_root=str(a.output),config=model_cfg,do_nomalize=True,return_item=True,chunk_size=50)
 batch=next(iter(DataLoader(ds,batch_size=2,num_workers=0)))
 assert batch['action.arm.position'].shape==(2,50,14) and batch['action.effector.position'].shape==(2,50,2)
 assert batch['action_is_pad'].shape==(2,50)
 item=ds[0];padded=ds.feature_transform.pad_and_concat(copy.deepcopy(item))
 assert padded['state'].shape==(51,) and padded['action'].shape==(50,51)
 model_state=prepare_state(padded,55);model_action=prepare_action(padded,55)
 assert model_state.shape[-1]==55 and model_action.shape[-2:]==(50,55)
 assert padded['action_joint_mask'].sum().item()==16 and padded['action_joint_mask'][:14].all() and padded['action_joint_mask'][28:30].all()
 for im in padded['image'].values():assert im.dtype==torch.uint8 and im.shape==(3,224,224)
 unnorm=ds.feature_transform.normalizer.unnormalize(copy.deepcopy(item));raw=ds.dataset[0]
 assert np.allclose(unnorm['action.arm.position']+raw['observation.state'][:14].numpy(),raw['action'][:,:14].numpy(),atol=1e-6)
 assert np.allclose(unnorm['action.effector.position'],raw['action'][:,14:].numpy(),atol=1e-6)
 reports.append({'split':split,'frames':len(ds),'normalized_arm_batch':list(batch['action.arm.position'].shape),'normalized_gripper_batch':list(batch['action.effector.position'].shape),'category_padded_action':list(padded['action'].shape),'model_padded_action':list(model_action.shape),'valid_internal_dimensions':16,'padding_mask_true':batch['action_is_pad'].sum(1).tolist(),'denormalization_roundtrip':'PASS'})
assert before==(a.output/'normalization.json').read_bytes()
report={'status':'PASS_OFFLINE','scope':'real upstream VLADataset + FeatureTransform + torch DataLoader before processor/tokenizer; actual pad_and_concat','full_training_collator':'NOT_RUN','model':'NOT_RUN','upstream_commit':audit['commit'],'import_mode':'leaf packages; unrelated eager distributed initialization skipped','versions':{k:importlib.metadata.version(k) for k in ('lerobot','torch','datasets')},'stats_sha256':hashlib.sha256(before).hexdigest(),'records':reports}
(root/'validation/phase2/lingbot_batch.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
