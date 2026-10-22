#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if r.wasSuccessful() else 1)
