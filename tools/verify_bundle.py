#!/usr/bin/env python3
"""Inspect archive and manifest without extraction. Reject traversal, links and extra members."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def verify(path):
    path=Path(path)
    sidecar=path.with_name(path.name+'.sha256')
    expected=sidecar.read_text().split()[0]
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if expected!=actual:raise ValueError('archive SHA-256 mismatch')
    contents={}
    with tarfile.open(path,'r:gz') as tar:
        for m in tar:
            name=PurePosixPath(m.name)
            if name.is_absolute() or '..' in name.parts or len(name.parts)<2:raise ValueError('unsafe archive path')
            if name.parts[0]!='dual-fr3-vla-platform':raise ValueError('unexpected archive root')
            if not m.isfile() or m.issym() or m.islnk():raise ValueError('links/non-regular members forbidden')
            if m.name in contents or m.size>2_000_000:raise ValueError('duplicate/oversized member')
            contents[m.name]=tar.extractfile(m).read()
    prefix='dual-fr3-vla-platform/'
    lines=contents[prefix+'migration/FILES.sha256'].decode().splitlines()
    names=set()
    for line in lines:
        sha,rel=line.split('  ',1)
        if rel in names:raise ValueError('duplicate checksum entry')
        names.add(rel)
        data=contents[prefix+rel]
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('member checksum mismatch: '+rel)
    members={n[len(prefix):] for n in contents}
    if names != members-{'migration/FILES.sha256'}:raise ValueError('checksum coverage mismatch')
    manifest=json.loads(contents[prefix+'migration/assets.manifest.json'])
    indexed={a['target_relative_path'] for a in manifest['files']}
    if indexed != members-{'migration/FILES.sha256','migration/assets.manifest.json'}:raise ValueError('asset manifest coverage mismatch')
    for a in manifest['files']:
        b=contents[prefix+a['target_relative_path']]
        if len(b)!=a['size_bytes'] or hashlib.sha256(b).hexdigest()!=a['sha256']:raise ValueError('asset manifest integrity mismatch')
    return {'archive':path.name,'bytes':path.stat().st_size,'sha256':actual,'files':len(contents),'status':'PASS_OFFLINE','links':0,'path_traversal':0,'checksum_coverage':'all regular files; checksum file excludes itself'}

if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
