import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify_bundle import verify

class BundleTests(unittest.TestCase):
    def test_archive_traversal_rejected(self):
        base=Path(__file__).resolve().parents[1]/'artifacts/test-tmp';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as d:
            p=Path(d)/'bad.tar.gz'
            with tarfile.open(p,'w:gz') as tar:
                item=tarfile.TarInfo('dual-fr3-vla-platform/../escape');item.size=1
                tar.addfile(item,io.BytesIO(b'x'))
            p.with_name(p.name+'.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
            with self.assertRaises(ValueError):verify(p)
    def test_archive_tamper_rejected(self):
        base=Path(__file__).resolve().parents[1]/'artifacts/test-tmp';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as d:
            p=Path(d)/'bad.tar.gz';p.write_bytes(b'changed')
            p.with_name(p.name+'.sha256').write_text('0'*64+'  bad.tar.gz\n')
            with self.assertRaises(ValueError):verify(p)
