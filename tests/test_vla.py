import unittest,copy
from fr3_platform.synthetic import state
from fr3_platform.control import OfflineExecutor
from fr3_platform.vla import ChunkScheduler,physical_state,SEMANTICS
from fr3_platform.contracts import ContractError
class VLATests(unittest.TestCase):
 def setUp(self):
  class Sink:
   source='simulation'
   def __init__(self):self.sent=[];self.held=False
   def send(self,x):self.sent.append(x)
   def hold(self):self.held=True
  self.sink=Sink();one={'lower':[-1.]*7,'upper':[1.]*7,'velocity':[2.]*7,'gripper':{'min_m':0.,'max_m':.1,'speed_m_s':1.}}
  self.e=OfflineExecutor(self.sink,{'source':'synthetic test','max_age_ns':100_000_000,'min_period_s':.001,'left':one,'right':copy.deepcopy(one)})
  self.s=state();self.q=physical_state(self.s);self.scheduler=ChunkScheduler(self.e)
 def test_valid_scheduled_and_exhausted(self):
  self.scheduler.install([self.q],self.s,1_001_000_000,semantics=SEMANTICS)
  self.assertIsNotNone(self.scheduler.submit_due(self.s,1_001_000_000))
  self.assertIsNone(self.scheduler.submit_due(self.s,1_002_000_000))
  self.assertIsNone(self.scheduler.submit_due(self.s,1_101_000_000));self.assertTrue(self.sink.held);self.assertIsNone(self.e.owner)
 def test_unknown_semantics_and_stale(self):
  for semantics,now in [('normalized_model_tensor',1_001_000_000),(SEMANTICS,2_000_000_000)]:
   with self.assertRaises(ContractError):self.scheduler.install([self.q],self.s,now,semantics=semantics)
 def test_bad_dimension_and_nan(self):
  for q in ([0]*55,[float('nan')]*16):
   with self.assertRaises(ContractError):self.scheduler.install([q],self.s,1_001_000_000,semantics=SEMANTICS)
 def test_invalid_prediction_holds_and_revokes(self):
  self.q[0]=99;self.scheduler.install([self.q],self.s,1_001_000_000,semantics=SEMANTICS)
  with self.assertRaises(ContractError):self.scheduler.submit_due(self.s,1_001_000_000)
  self.assertTrue(self.sink.held);self.assertEqual(self.sink.sent,[]);self.assertIsNone(self.e.owner)
 def test_conflicting_vr_authority(self):
  self.e.acquire('vr',1_000_000_000,100_000_000);self.scheduler.install([self.q],self.s,1_001_000_000,semantics=SEMANTICS)
  with self.assertRaises(ContractError):self.scheduler.submit_due(self.s,1_001_000_000)
  self.assertEqual(self.sink.sent,[]);self.assertEqual(self.e.owner,'vr')
