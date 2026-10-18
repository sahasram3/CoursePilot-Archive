import unittest
from src.graph_optimizer import PlanningRequest, optimize_graph, ScheduleError
from src.prerequisite_graph import CourseRule, Alternative
from src.planner import terms
URL='https://catalog.unc.edu/courses/math/'
def r(code,clauses=(),credits=3):
    return CourseRule(code,credits,tuple(tuple(Alternative(*a) if isinstance(a,tuple) else Alternative(a) for a in clause) for clause in clauses),URL,'Test fixture: synthetic, not a catalog transcription')
RULES={'A':r('A'), 'B':r('B',(('A',),)), 'C':r('C',(('B','X'),)), 'D':r('D',((('A','B'),),))}
CAL=terms(2026,'Fall',2027,'Fall')
class GraphOptimizerTests(unittest.TestCase):
    def test_chain(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('A','B','C')),limit=3)
        self.assertTrue(p['alternatives'])
        for alt in p['alternatives']:
            self.assertLess(next(i for i,t in enumerate(alt['terms'].values()) if 'A' in t),next(i for i,t in enumerate(alt['terms'].values()) if 'B' in t))
    def test_or(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('C',),completed=('X',)))
        self.assertTrue(p['alternatives'])
    def test_grade_minimum_blocks_unknown(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('D',),completed=('A',)))
        self.assertFalse(p['alternatives'])
        self.assertTrue(optimize_graph(RULES,CAL,PlanningRequest(('D',),completed=('A',)),grades={'A':'B'})['alternatives'])
    def test_unreviewed_fails(self):
        with self.assertRaises(ScheduleError):optimize_graph(RULES,CAL,PlanningRequest(('UNKNOWN',)))
    def test_lock_infeasible(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('A','B'),locked=(('B','Fall 2026'),)))
        self.assertFalse(p['alternatives'])
    def test_max_credits(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('A','B'),max_credits=3))
        self.assertTrue(p['alternatives'])
        self.assertTrue(all(v<=3 for a in p['alternatives'] for v in a['credits'].values()))
    def test_nonzero_minimum_does_not_fake_courses(self):
        self.assertFalse(optimize_graph(RULES,CAL,PlanningRequest(('A',),min_credits=12))['alternatives'])
    def test_empty_terms_and_horizon(self):
        p=optimize_graph(RULES,CAL,PlanningRequest(('A',)),limit=1)
        self.assertEqual(len(p['alternatives'][0]['terms']),3)
if __name__=='__main__':unittest.main()
