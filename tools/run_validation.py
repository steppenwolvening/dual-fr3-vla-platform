#!/usr/bin/env python3
"""Bounded offline verification orchestrator. Requires existing explicit interpreters."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--lerobot-python',type=Path,required=True)
p.add_argument('--mujoco-python',type=Path,required=True)
a=p.parse_args()
run=ROOT/'artifacts'/('validation-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
run.mkdir(exist_ok=False)
(run/'tmp').mkdir()
env=dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',HF_HOME=str(run/'hf-cache'),
           HF_DATASETS_CACHE=str(run/'hf-cache/datasets'),HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',
           HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',XDG_CACHE_HOME=str(run/'cache'),
           MPLCONFIGDIR=str(run/'mpl'),CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',TMPDIR=str(run/'tmp'))
commands=[
 ('core_unit',sys.executable,['tools/test.py'],'PASS_UNIT','synthetic unit fixtures'),
 ('synthetic',sys.executable,['tools/fr3.py','synthetic',str(run/'episode')],'PASS_OFFLINE','8 synthetic RGB/depth/tactile frames'),
 ('validator',sys.executable,['tools/fr3.py','validate',str(run/'episode')],'PASS_OFFLINE','canonical synthetic episode'),
 ('replay',sys.executable,['tools/fr3.py','replay',str(run/'episode')],'PASS_OFFLINE','canonical synthetic episode'),
 ('twin_protocol',sys.executable,['tools/fr3.py','twin-publish',str(run/'episode')],'PASS_OFFLINE','recorded state JSONL; not two simulators'),
 ('lerobot_reader',str(a.lerobot_python),['tools/fr3.py','export-lerobot',str(run/'episode'),str(run/'lerobot'),'--label','sent','--fps','10','--tolerance-ms','20'],'PASS_OFFLINE','synthetic train-only explicit profile; real LeRobot reader'),
 ('mujoco_engine',str(a.mujoco_python),['tools/mujoco_engine_smoke.py'],'PASS_SIM','primitive sphere only; not FR3 model'),
]
results=[]
for name,python,args,passed,input_type in commands:
    cmd=[python,'-B',*args]
    r=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=90)
    log=ROOT/'validation'/f'{name}.log'
    log.write_text(r.stdout+r.stderr)
    results.append({'name':name,'command':cmd,'interpreter':python,'input':input_type,'exit_code':r.returncode,
                    'status':passed if r.returncode==0 else 'FAIL','log':str(log.relative_to(ROOT))})
    print(name,results[-1]['status'],flush=True)
    if r.returncode:print((r.stdout+r.stderr)[-4000:],flush=True)
for path in list((ROOT/'src').rglob('*.py'))+list((ROOT/'tools').glob('*.py'))+list((ROOT/'tests').glob('*.py')):
    ast.parse(path.read_text(),filename=str(path))
results.append({'name':'static_parse','status':'PASS_UNIT','input':'all authored Python files','command':['ast.parse'],'interpreter':sys.executable,'exit_code':0})
audit=json.loads((ROOT/'migration/phase1-audit.json').read_text())
changed=[]
for f in audit['source_files']:
    p=Path(f['path'])
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:changed.append(f['path'])
results.append({'name':'source_files_unchanged','status':'PASS_OFFLINE' if not changed else 'FAIL','checked_files':len(audit['source_files']),'changed':changed,'evidence':'FILE_VERIFIED','exit_code':bool(changed)})
record={'recorded_utc':datetime.now(timezone.utc).isoformat(),'run_directory':str(run),'tests':results,
        'prohibited_actions_executed':False,'overall_scope':'offline foundation only; unresolved integrations explicitly BLOCKED'}
# Exact interpreter paths belong to provenance evidence, never runtime defaults.
(ROOT/'migration/validation-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
summary={'tests':[{k:v for k,v in x.items() if k not in ('command','interpreter','changed')} for x in results], 'scope':record['overall_scope']}
(ROOT/'validation/results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'run_directory':str(run),'all_requested_offline_checks_passed':all(not x['exit_code'] for x in results)}))
sys.exit(0 if all(not x['exit_code'] for x in results) else 1)
