"""Regression checks for mixed-origin recording; no optional simulation imports."""
import unittest,copy
from fr3_platform.data import validate_source
from fr3_platform.contracts import ContractError

class SourceTests(unittest.TestCase):
 def test_mixed_source_declarations(self):
  meta={'synthetic':False,'stream_sources':{'state':'simulation','rgb':'synthetic'}}
  validate_source({'stream':'state','source':'simulation'},meta)
  validate_source({'stream':'rgb','source':'synthetic'},meta)
  with self.assertRaises(ContractError):validate_source({'stream':'state','source':'hardware'},meta)
 def test_legacy_synthetic(self):
  validate_source({'source':'synthetic'}, {'synthetic':True})
  with self.assertRaises(ContractError):validate_source({'source':'simulation'}, {'synthetic':True})
