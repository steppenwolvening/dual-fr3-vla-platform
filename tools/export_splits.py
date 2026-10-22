#!/usr/bin/env python3
import sys,os,json,argparse
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
for k in ('HF_HUB_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[k]='1'
from fr3_platform.dataset_v2 import export_split
p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
m=json.loads(a.manifest.read_text());a.output.mkdir(parents=True,exist_ok=False)
reports=[]
for split in ('train','validation','test'):
 reports.append(export_split(m['episodes'][split],a.output/split,split=split,cameras=m['cameras'],label=m['label'],fps=m['fps'],tolerance_ns=m['tolerance_ns'],training_stats=None if split=='train' else a.output/'train/training_statistics.json'))
assert len({r['stats_sha256'] for r in reports})==1
(root/'validation/phase2/lerobot_splits.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
