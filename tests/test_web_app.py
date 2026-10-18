import unittest
from server import plan,DEMO_PROGRAMS
class WebTests(unittest.TestCase):
 def test_provisional_sequence(self):
  result=plan({'program':'mathematics-major-ba','start':'Fall 2026','graduation':'Spring 2029','completed':['MATH 231'],'grades':{'MATH 231':'A'}})
  self.assertTrue(result['alternatives'])
  self.assertIn('not a complete',result['scope'])
 def test_unverified_blocked(self):
  with self.assertRaisesRegex(ValueError,'not been verified'):plan({'program':'neuroscience-minor'})
 def test_unknown_courses_blocked(self):
  with self.assertRaisesRegex(ValueError,'supported demonstration'):plan({'program':'mathematics-major-ba','required':['FAKE 100']})
 def test_all_discovered_not_claimed(self):
  self.assertTrue(all(p['status'] in ('partial','unverified') for p in DEMO_PROGRAMS))
 def test_infeasible_horizon(self):
  result=plan({'program':'mathematics-major-ba','start':'Fall 2026','graduation':'Fall 2026'})
  self.assertFalse(result['alternatives'])
if __name__=='__main__':unittest.main()
