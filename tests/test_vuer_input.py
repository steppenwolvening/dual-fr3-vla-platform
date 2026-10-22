import unittest
from fr3_platform.vuer_input import controller_frame
from fr3_platform.contracts import ContractError
class VuerTests(unittest.TestCase):
 def test_column_major_buttons_and_missing_arm(self):
  raw={'left':[1,0,0,0,0,1,0,0,0,0,1,0,.1,.2,.3,1],'leftState':{'squeeze':True,'thumbstick':False,'bButton':False,'triggerValue':.25}}
  result=controller_frame(raw,sequence=1,received_ns=12,origin='synthetic-test',buttons={'deadman':'squeeze','clutch':'thumbstick','recenter':'bButton','gripper':'triggerValue'})
  self.assertEqual([r[3] for r in result['hands']['left']['world_from_grip']],[.1,.2,.3,1]);self.assertAlmostEqual(result['hands']['left']['opening_width_m'],.06)
  self.assertTrue(result['hands']['left']['deadman']);self.assertFalse(result['hands']['right']['tracking']);self.assertFalse(result['hands']['right']['deadman'])
 def test_unconfigured_origin_rejected(self):
  with self.assertRaises(ContractError):controller_frame({},sequence=1,received_ns=12,origin='UNCONFIGURED',buttons={})
