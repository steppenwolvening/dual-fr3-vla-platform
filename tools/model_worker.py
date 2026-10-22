#!/usr/bin/env python3
"""JSONL model-only process. Parent owns all robot/simulator execution."""
import argparse,sys,json,contextlib,time,os
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
p=argparse.ArgumentParser();p.add_argument('--model',choices=['pi05_native','lingbot_vla_v2'],required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--profile',required=True);p.add_argument('--robot-config');p.add_argument('--norm-stats');p.add_argument('--runtime-source');p.add_argument('--execute-model',action='store_true');a=p.parse_args()
if not a.execute_model:print(json.dumps({'status':'NOT_RUN','requires':'separate model execution approval and a reviewed dual-FR3 checkpoint'}));sys.exit(0)
for name in ('HF_HUB_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[name]='1'
if a.runtime_source:sys.path.insert(0,str(Path(a.runtime_source).resolve()))
with contextlib.redirect_stdout(sys.stderr):
 from fr3_platform.vla_runtimes import NativePI05,LingBotV2
 import numpy as np
 runtime=NativePI05(a.checkpoint,a.profile) if a.model=='pi05_native' else LingBotV2(a.checkpoint,a.profile,a.robot_config,a.norm_stats)
print(json.dumps({'status':'MODEL_LOADED','model':a.model}),flush=True)
for line in sys.stdin:
 request=json.loads(line);t0=time.monotonic_ns()
 with contextlib.redirect_stdout(sys.stderr):
  images={k:np.asarray(v,dtype=np.uint8) for k,v in request['images'].items()}
  actions=runtime.predict(request['state'],images,request['instruction'])
 print(json.dumps({'actions':actions,'inference_latency_ns':time.monotonic_ns()-t0,'model':a.model}),flush=True)
