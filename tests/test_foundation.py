import unittest,sys
sys.path.insert(0,'src')
from planner import *
from catalog import discover
class Tests(unittest.TestCase):
 def test_terms(self):
  x=terms(2026,'Fall',2028,'Spring');self.assertEqual([t.label for t in x],['Fall 2026','Spring 2027','Fall 2027','Spring 2028'])
 def test_summer(self):self.assertIn('Summer 2027',[t.label for t in terms(2026,'Fall',2028,'Spring',True)])
 def test_unknown(self):
  with self.assertRaisesRegex(ValueError,'Unverified'):build({'X':Course('X',3)},['X'],[],terms(2026,'Fall',2027,'Spring'))
 def test_prereq(self):
  c={'A':Course('A',3,verified=True),'B':Course('B',3,('A',),True)}
  with self.assertRaisesRegex(ValueError,'Prerequisite'):validate_plan(c,{'Fall 2026':['A','B']},[],0)
 def test_credit(self):
  c={'A':Course('A',4,verified=True)}
  with self.assertRaisesRegex(ValueError,'Credit'):validate_plan(c,{'Fall 2026':['A']},[],12)
 def test_discovery(self):
  h='<a href="/undergraduate/programs-study/mathematics-major-ba/">Mathematics Major, B.A.</a>'
  self.assertEqual(len(discover(h)),1)
if __name__=='__main__':unittest.main()
