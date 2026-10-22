#!/usr/bin/env python3
"""Fetch only the pinned small source-text audit subset, never model weights."""
import json,hashlib,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1];pin=json.loads((root/'environments/lingbot-source.json').read_text());dest=root/'.deps/lingbot-audit';dest.mkdir(parents=True,exist_ok=True)
for item in pin['files']:
 path=Path(item['path']);assert not path.is_absolute() and '..' not in path.parts
 url=f"https://raw.githubusercontent.com/Robbyant/lingbot-vla-v2/{pin['commit']}/{path}"
 with urllib.request.urlopen(url,timeout=20) as response:data=response.read(item['size']+1)
 assert len(data)==item['size'] and hashlib.sha256(data).hexdigest()==item['sha256']
 output=dest/path;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
(dest/'audit.json').write_text(json.dumps(pin,indent=2)+'\n');print('Pinned source subset verified; no dependency installation, no model weights')
