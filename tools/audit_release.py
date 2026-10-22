#!/usr/bin/env python3
"""Scan every reachable Git blob and current tracked working file; never print secrets."""
import subprocess,re,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
patterns={
 'github_token':rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
 'openai_token':rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b',
 'aws_access_key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'credential_url':rb'https?://[^\s/:]+:[^\s/@]+@',
}
findings=[];privacy=[];blobs=0;largest=0
for row in git('rev-list','--objects','--all').decode().splitlines():
 oid,_,name=row.partition(' ')
 if git('cat-file','-t',oid).strip()!=b'blob':continue
 data=git('cat-file','blob',oid);blobs+=1;largest=max(largest,len(data))
 for label,pattern in patterns.items():
  if re.search(pattern,data):findings.append({'object':oid,'path':name,'pattern':label})
 if b'/home/aning/' in data or b'aning-ROG-' in data:privacy.append({'object':oid,'path':name,'contains':'source account/home/host metadata'})
tracked=git('ls-files','-z').decode().split('\0')[:-1]
for name in tracked:
 path=Path(name)
 if path.parts[0] in ('.deps','.venv-sim','artifacts','weights','checkpoints','datasets') or path.suffix in ('.pem','.key','.pt','.pth','.ckpt','.safetensors'):
  findings.append({'path':name,'pattern':'excluded_asset'})
 data=(root/path).read_bytes()
 for label,pattern in patterns.items():
  if re.search(pattern,data):findings.append({'path':name,'pattern':label,'tree':'working'})
report={'status':'PASS_KNOWN_PATTERNS' if not findings else 'REVIEW_REQUIRED','head':git('rev-parse','HEAD').decode().strip(),'reachable_commits':len(git('rev-list','--all').splitlines()),'reachable_blobs':blobs,'tracked_files':len(tracked),'tracked_bytes':sum((root/p).stat().st_size for p in tracked),'largest_historical_blob_bytes':largest,'findings':findings,'privacy_metadata':privacy,'limitations':'Known-pattern scan only; owner/IP/license review required. Full history preserved, not rewritten.'}
out=root/'artifacts/release-audit.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='privacy_metadata'},indent=2));print('privacy_metadata_blobs:',len(privacy));raise SystemExit(0 if not findings else 1)
