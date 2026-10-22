#!/usr/bin/env python3
"""Source archive + preserved-history Git bundle; no uploads and no raw data."""
from pathlib import Path
import subprocess,json,hashlib,tarfile,io,tempfile,gzip,sys
root=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
assert not git('status','--porcelain').strip(),'commit reviewed changes before packaging'
subprocess.run([sys.executable,'-B',str(root/'tools/audit_release.py')],cwd=root,check=True)
commit=git('rev-parse','HEAD').decode().strip();files=git('ls-files','-z').decode().split('\0')[:-1]
folder='dual-fr3-vla-platform-0.2.0.dev1-'+commit[:12];out=root/'artifacts/dist';out.mkdir(parents=True,exist_ok=True)
archive=out/(folder+'.tar.gz');assert not archive.exists(),'new artifact required'
manifest={'commit':commit,'baseline':'10922064d313b9af45a28d6c94c852ccd0ee1f3b','version':'0.2.0.dev1','files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}}
epoch=int(git('show','-s','--format=%ct','HEAD'))
with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=epoch,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
 for name in files:
  assert not (root/name).is_symlink(),'source archive must not dereference links'
  content=(root/name).read_bytes();info=tarfile.TarInfo(folder+'/'+name);info.size=len(content);info.mtime=epoch;info.mode=0o644;tar.addfile(info,io.BytesIO(content))
 content=json.dumps(manifest,sort_keys=True,indent=2).encode();info=tarfile.TarInfo(folder+'/RELEASE_MANIFEST.json');info.size=len(content);info.mtime=epoch;tar.addfile(info,io.BytesIO(content))
bundle=out/(folder+'.bundle');subprocess.run(['git','bundle','create',str(bundle),'--all'],cwd=root,check=True);subprocess.run(['git','bundle','verify',str(bundle)],cwd=root,check=True,capture_output=True)
with tempfile.TemporaryDirectory(dir=root/'artifacts') as tmp:
 with tarfile.open(archive) as tar:tar.extractall(tmp,filter='data')
 extracted=Path(tmp)/folder
 for name,sha in manifest['files'].items():assert hashlib.sha256((extracted/name).read_bytes()).hexdigest()==sha
 result=subprocess.run([sys.executable,'-B','tools/test.py'],cwd=extracted,text=True,capture_output=True)
 (out/(folder+'-restore.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,'archive restore regressions failed'
result={'commit':commit,'files':len(files),'restored_tests':'PASS','artifacts':[]}
for path in (archive,bundle):
 sha=hashlib.sha256(path.read_bytes()).hexdigest();path.with_name(path.name+'.sha256').write_text(sha+'  '+path.name+'\n');result['artifacts'].append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha})
(out/(folder+'-report.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
