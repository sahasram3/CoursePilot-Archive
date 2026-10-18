import unittest
from src.degree_rules import Requirement,Program
from src.planner import Course,terms
from src.degree_optimizer import candidate_sets,generate,PlanningError
URL='https://catalog.unc.edu/undergraduate/programs-study/'
def req(id,kind,cs,count):return Requirement(id,kind,tuple(cs),count,URL,'2026-2027',True)
def prog(*rs):return Program('TEST MAJOR','major',tuple(rs),URL,'2026-2027',True)
class DegreeOptimizerTests(unittest.TestCase):
 def test_any_and_completed(self):
  p=prog(req('r','ANY',['A','B'],1))
  self.assertEqual(list(candidate_sets([p],['A'],{})),[set()])
 def test_choice_sets(self):
  p=prog(req('r','ANY',['A','B'],1))
  self.assertEqual(list(candidate_sets([p],[],{})),[{'A'},{'B'}])
 def test_unverified_blocks(self):
  p=Program('TEST','major',(req('r','ALL',['A'],1),),URL,'2026-2027',False)
  with self.assertRaises(PlanningError):list(candidate_sets([p],[],{}))
 def test_full_horizon_and_alternatives(self):
  p=prog(req('r','ANY',['A','B'],1),req('s','ALL',['C'],1))
  cs={x:Course(x,3,(),True) for x in 'ABC'}
  result=generate([p],cs,[],terms(2026,'Fall',2027,'Spring'),min_credits=0,max_credits=18)
  self.assertEqual(len(result['alternatives']),2)
  self.assertEqual(set(result['alternatives'][0]['terms']),{'Fall 2026','Spring 2027'})
 def test_no_fabricated_credits(self):
  p=prog(req('r','ALL',['A'],1))
  result=generate([p],{'A':Course('A',0,(),True)},[],terms(2026,'Fall',2026,'Fall'),min_credits=0)
  self.assertFalse(result['alternatives'])
 def test_prereq_order(self):
  p=prog(req('r','ALL',['A','B'],2))
  cs={'A':Course('A',3,(),True),'B':Course('B',3,('A',),True)}
  result=generate([p],cs,[],terms(2026,'Fall',2027,'Spring'),min_credits=0)
  self.assertTrue(result['alternatives'])
  plan=result['alternatives'][0]['terms']
  self.assertEqual(plan['Fall 2026'],['A'])
  self.assertEqual(plan['Spring 2027'],['B'])
if __name__=='__main__':unittest.main()
