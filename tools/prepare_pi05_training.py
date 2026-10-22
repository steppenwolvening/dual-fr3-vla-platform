#!/usr/bin/env python3
"""Serialize a real native PI05 TrainPipelineConfig; does not train or load weights."""
import argparse,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from fr3_platform.exporter import PROFILE
from lerobot.configs import PolicyFeature,FeatureType
from lerobot.configs.default import DatasetConfig
from lerobot.configs.train import TrainPipelineConfig
from lerobot.configs.accelerator import AcceleratorConfig,GradientAccumulationConfig
from lerobot.policies.pi05.configuration_pi05 import PI05Config
p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('output',type=Path);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--tokenizer',required=True);a=p.parse_args()
policy=PI05Config(device='cuda',dtype='bfloat16',chunk_size=50,n_action_steps=5,train_expert_only=True,freeze_vision_encoder=True,gradient_checkpointing=True,compile_model=False,use_relative_actions=False,text_tokenizer_name=a.tokenizer,push_to_hub=False,pretrained_path=a.checkpoint,action_feature_names=PROFILE,input_features={'observation.state':PolicyFeature(type=FeatureType.STATE,shape=(16,)),**{'observation.images.'+c:PolicyFeature(type=FeatureType.VISUAL,shape=(3,224,224)) for c in ('head','left_wrist','right_wrist')}},output_features={'action':PolicyFeature(type=FeatureType.ACTION,shape=(16,))})
policy.device='cuda' # serialize intended target even during a CPU-only config check
cfg=TrainPipelineConfig(dataset=DatasetConfig(repo_id='local/dual-fr3-train',root=str(a.dataset),use_imagenet_stats=False),policy=policy,output_dir=Path('artifacts/pi05-training'),batch_size=1,num_workers=0,steps=1000,save_freq=100,log_freq=10,env_eval_freq=0,eval_steps=0,accelerator=AcceleratorConfig(mixed_precision='bf16',gradient_accumulation=GradientAccumulationConfig(steps=8)))
a.output.mkdir(parents=True,exist_ok=False);cfg._save_pretrained(a.output)
loaded=TrainPipelineConfig.from_pretrained(a.output,local_files_only=True)
assert loaded.policy.chunk_size==50 and loaded.batch_size==1 and not loaded.policy.push_to_hub
print('PASS_OFFLINE: real TrainPipelineConfig serialized and reread; training NOT_RUN, memory capacity NOT_VERIFIED')
