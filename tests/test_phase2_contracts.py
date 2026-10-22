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

class SplitTests(unittest.TestCase):
 def test_three_way_disjoint(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  from fr3_platform.dataset_v2 import validate_split_manifest
  manifest={'episodes':{s:[s] for s in ('train','validation','test')}}
  with patch('fr3_platform.dataset_v2.DatasetReader',side_effect=lambda p:SimpleNamespace(meta={'split':p,'episode_id':p})):
   self.assertEqual(validate_split_manifest(manifest),3)
  with patch('fr3_platform.dataset_v2.DatasetReader',side_effect=lambda p:SimpleNamespace(meta={'split':p,'episode_id':'train' if p=='train' else 'shared-evaluation'})):
   with self.assertRaises(ContractError):validate_split_manifest(manifest)
 def test_split_label_mismatch(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  from fr3_platform.dataset_v2 import validate_split_manifest
  with patch('fr3_platform.dataset_v2.DatasetReader',return_value=SimpleNamespace(meta={'split':'test','episode_id':'x'})):
   with self.assertRaises(ContractError):validate_split_manifest({'episodes':{'train':['x'],'validation':['y'],'test':['z']}})
