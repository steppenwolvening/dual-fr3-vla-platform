#!/usr/bin/env python3
"""Build a small source-only archive after explicit per-file admission and scanning."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from verify_bundle import verify

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_TOP={'README.md','pyproject.toml','.gitignore','THIRD_PARTY_NOTICES.md','LICENSE_REVIEW.md'}
ALLOWED_DIR={'src','tools','tests','configs','docs','environments','migration','validation'}
DENY_PARTS={'.git','__pycache__','.venv','node_modules','build','install','log','checkpoints','weights','datasets','artifacts'}
GENERATED={'migration/assets.manifest.json','migration/FILES.sha256'}
PURPOSE={
 'contracts.py':('统一状态、命令及多模态帧契约','Recorder/OfflineExecutor/tests'),
 'control.py':('离线单一命令入口及拒绝不安全命令','tests/test_core.py'),
 'data.py':('异步记录、校验、因果对齐、恢复与回放','tools/fr3.py; tests'),
 'synthetic.py':('独立标记 synthetic RGB-D/触觉 episode','fr3 synthetic; tests'),
 'exporter.py':('Canonical→固定 LeRobot writer/reader','fr3 export-lerobot; tests'),
 'teleop.py':('离线 translation/clutch 映射','tests/test_core.py'),
 'twin.py':('统一状态协议及受审模型 MuJoCo 回放','fr3 twin-publish/mujoco-replay; tests'),
 'sensors.py':('未配置设备拒绝与接口边界','tests/test_core.py'),
 'ros_state.py':('显式七关节映射及缺失字段处理','tests/test_core.py'),
 'preflight.py':('只读元数据与 ROS/Conda 污染检查','fr3 preflight; tests'),
 'cli.py':('无硬件离线命令入口','tools/fr3.py'),
 '__init__.py':('包版本标识','Python imports'),
 'fr3.py':('无需安装的源码启动器','README commands'),
 'test.py':('标准库测试启动器','README commands'),
 'test_core.py':('契约、安全拒绝、记录质量回归验证','tools/test.py'),
 'test_bundle.py':('归档校验拒绝篡改和路径攻击','tools/test.py'),
 'mujoco_engine_smoke.py':('20 步无硬件引擎冒烟','validation runner'),
 'capture_audit.py':('限定源文件与依赖元数据证据采集','Phase 1 source audit'),
 'build_bundle.py':('代码准入、来源清单与源包生成','README packaging'),
 'verify_bundle.py':('无解压校验源码归档','build_bundle; target restore'),
 'run_validation.py':('记录真实离线验证命令与结果','migration/VALIDATION.md')}


def admission(rel):
    if rel.name in PURPOSE:return PURPOSE[rel.name]
    if rel.parts[0]=='configs':return ('当前装配配置模板，未知值明确拒绝','配置审查; MuJoCoReplay; sensors tests')
    if rel.parts[0]=='environments':return ('隔离依赖/loader 固定依据','exporter pin check; target setup')
    if rel.parts[0]=='validation':return ('本次真实测试结果证据','STATUS/VALIDATION review')
    if rel.parts[0] in ('docs','migration') or rel.name in ALLOWED_TOP:return ('架构、契约、来源、恢复或许可审查依据','README/operator review')
    raise ValueError('file has no admission rationale: '+str(rel))


def collect():
    selected={}
    candidates=[]
    for base,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in DENY_PARTS]
        for d in dirs:
            if (Path(base)/d).is_symlink():raise ValueError('directory symlink rejected')
        candidates.extend(Path(base)/n for n in names)
    for p in sorted(candidates):
        rel=p.relative_to(ROOT)
        if any(x in DENY_PARTS for x in rel.parts):continue
        if p.is_symlink():raise ValueError('symlink rejected: '+str(rel))
        if not p.is_file():continue
        if str(rel) in GENERATED:continue
        if not (rel.parts[0] in ALLOWED_DIR or str(rel) in ALLOWED_TOP):continue
        if p.stat().st_size>2_000_000:raise ValueError('large file excluded: '+str(rel))
        if p.suffix.lower() in ('.pt','.pth','.ckpt','.safetensors','.mp4','.usd','.stl','.pem','.key'):raise ValueError('unapproved asset type')
        if re.search(r'(?:^|[_.-])(?:soarm101|so-arm101|robotiq|l20|o30|phase21|phase22|openpi|openvla|pi05|ppo)(?:[_.-]|$)',rel.name.lower()):raise ValueError('excluded legacy asset name')
        if rel.name.startswith(('.env','credentials','token')) or rel.suffix.lower() in ('.key','.pem'):raise ValueError('personal/secret filename')
        data=p.read_bytes();txt=data.decode('utf-8')
        patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}',r'\bhf_[A-Za-z0-9]{24,}',r'\bsk-[A-Za-z0-9_-]{30,}']
        if any(re.search(pattern,txt) for pattern in patterns):raise ValueError('possible secret in '+str(rel))
        if rel.parts[0] in ('src','tools','configs','environments','tests') and re.search(r'/home/(?:aning|shuteng)(?:/|\b)',txt):raise ValueError('old user absolute path in runtime surface')
        admission(rel)
        selected[str(rel)]=data
    return selected


def build(version, out):
    if not re.fullmatch('[A-Za-z0-9._-]+',version):raise ValueError('unsafe version')
    out=out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('output must stay inside staging')
    out.mkdir(parents=True,exist_ok=True)
    archive=out/f'dual-fr3-vla-platform-{version}.tar.gz'
    if archive.exists():raise FileExistsError(archive)
    selected=collect()
    files=[]
    for rel,data in selected.items():
        purpose,used=admission(Path(rel))
        files.append({'path':rel,'target_relative_path':rel,'size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                      'purpose':purpose,'used_by':used,'necessity':'supports current offline foundation or required audit/recovery',
                      'source':'newly authored in this staging; source evidence recorded separately',
                      'license':'UNASSIGNED_PENDING_LAB_POLICY','applicable_hardware':'Dual FR3 + Franka Gripper + D405 + FlexiTac; synthetic profiles explicitly separate',
                      'old_hardware_assumptions':False,'old_paths':'provenance only' if Path(rel).parts[0] in ('migration','validation') else False,
                      'transfer_status':'LOCAL_ONLY_NOT_TRANSFERRED','checksum_status':'SHA256_COMPUTED'})
    manifest={'schema':'fr3.assets/1','version':version,'files':files,'self_exclusions':['migration/assets.manifest.json','migration/FILES.sha256'],
              'generated_metadata_purpose':'manifest inventories payload files; FILES.sha256 covers manifest and all payload files except itself',
              'external_assets':[{'asset':'selected LingBot VLA 2 checkpoint and companions','path':'UNCONFIGURED','size_bytes':None,'status':'BLOCKED_NOT_LOCATED','copied':False},
                                 {'asset':'assembly-verified FR3/Franka Gripper meshes/URDF/MJCF/USD and calibrations','path':'UNCONFIGURED','status':'BLOCKED_APPLICABILITY_UNKNOWN','copied':False}]}
    blob=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    (ROOT/'migration/assets.manifest.json').write_bytes(blob)
    selected['migration/assets.manifest.json']=blob
    hashes=''.join(hashlib.sha256(data).hexdigest()+'  '+rel+'\n' for rel,data in sorted(selected.items())).encode()
    (ROOT/'migration/FILES.sha256').write_bytes(hashes)
    selected['migration/FILES.sha256']=hashes
    with archive.open('xb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w') as tar:
                for rel,data in sorted(selected.items()):
                    info=tarfile.TarInfo('dual-fr3-vla-platform/'+rel)
                    info.size=len(data);info.mode=0o644;info.mtime=0;info.uid=info.gid=0
                    tar.addfile(info,io.BytesIO(data))
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name+'.sha256').write_text(sha+'  '+archive.name+'\n')
    result=verify(archive)
    archive.with_name(archive.name+'.verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--output',type=Path,default=ROOT/'artifacts/dist')
    a=p.parse_args();print(json.dumps(build(a.version,a.output),indent=2))
