import unittest
from src.degree_rules import Program,Requirement,audit,validate_combination,source_coverage
URL='https://catalog.unc.edu/undergraduate/programs-study/'
def p(name,kind='major',rules=()):return Program(name,kind,tuple(rules),URL,'2026-2027',True)
def r(name,kind,courses,count=1):return Requirement(name,kind,tuple(courses),count,URL,'2026-2027',True)
class Tests(unittest.TestCase):
 def test_combinations(self):
  for ps in [[p('a')],[p('a'),p('b')],[p('a'),p('m','minor')],[p('a'),p('b'),p('m','minor')],[p('a'),p('m','minor'),p('n','minor')]]:validate_combination(ps)
  for ps in [[p('a'),p('b'),p('c')],[p('a'),p('b'),p('m','minor'),p('n','minor')],[p('m','minor')]]:
   with self.assertRaises(ValueError):validate_combination(ps)
 def test_audit_and_or(self):
  result=audit([p('test',rules=[r('core','ALL',['A','B']),r('choice','ANY',['C','D']),r('electives','AT_LEAST',['E','F','G'],2)])],['A','D','E'],['B'])
  self.assertEqual([x['status'] for x in result],['in_progress','satisfied','remaining'])
  self.assertEqual(result[2]['still_needed'],1)
 def test_unverified_rejected(self):
  with self.assertRaises(ValueError):audit([Program('unknown','major',(),URL,'2026-2027',False)],[])
 def test_coverage(self):
  self.assertEqual(source_coverage([p('a',rules=[r('x','ANY',['A'])])])['coverage'],1)
if __name__=='__main__':unittest.main()
