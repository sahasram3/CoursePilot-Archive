import unittest
from src.prerequisite_graph import eligible, validate_sequence, explain, dependency_edges
from src.math_prerequisites_2026 import RULES
from src.program_coverage import registry_from_index,coverage

class TestGraph(unittest.TestCase):
 def test_math_232_grade(self):
  self.assertFalse(eligible(RULES['MATH 232'],{'MATH 231'},grades={'MATH 231':'D'})[0])
  self.assertTrue(eligible(RULES['MATH 232'],{'MATH 231'},grades={'MATH 231':'C-'})[0])
 def test_placement(self):
  self.assertTrue(eligible(RULES['MATH 232'],set(),permissions={'PLACEMENT:MATH232'})[0])
 def test_math_521_and_or(self):
  self.assertFalse(eligible(RULES['MATH 521'],{'MATH 233'})[0])
  self.assertTrue(eligible(RULES['MATH 521'],{'MATH 233','MATH 381'})[0])
 def test_stor_grade(self):
  self.assertFalse(eligible(RULES['MATH 521'],{'MATH 233','STOR 215'},grades={'STOR 215':'B+'})[0])
  self.assertTrue(eligible(RULES['MATH 521'],{'MATH 233','STOR 215'},grades={'STOR 215':'A-'})[0])
 def test_same_term_rejected(self):
  self.assertTrue(validate_sequence([['MATH 233','MATH 383']],RULES,completed={'MATH 232'}))
 def test_sequential(self):
  self.assertEqual(validate_sequence([['MATH 233'],['MATH 383']],RULES,completed={'MATH 232'}),[])
 def test_unknown_course_blocked(self):
  self.assertTrue(validate_sequence([['CHEM 101']],RULES))
 def test_explain(self):
  self.assertIn('MATH 383',explain('MATH 233',RULES)['unlocks'])
 def test_edges(self):
  self.assertIn(('MATH 233','MATH 383'),dependency_edges(RULES))
 def test_university_registry(self):
  html='<a href="/undergraduate/programs-study/mathematics-major-ba/">Mathematics Major, B.A.</a><a href="/undergraduate/programs-study/biology-minor/">Biology Minor</a>'
  reg=registry_from_index(html)
  self.assertEqual(coverage(reg,reviewed_ids=['mathematics-major-ba'])['discovered'],2)
  self.assertEqual(coverage(reg)['plan_ready'],0)
 def test_no_false_ready(self):
  html='<a href="/undergraduate/programs-study/biology-minor/">Biology Minor</a>'
  with self.assertRaises(ValueError): coverage(registry_from_index(html),plan_ready_ids=['biology-minor'])
if __name__=='__main__':unittest.main()
