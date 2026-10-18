import unittest
from src.graph_optimizer import optimize_graph, PlanningRequest, ScheduleError
from src.prerequisite_graph import CourseRule, Alternative
from src.planner import terms
U='https://catalog.unc.edu/courses/math/'
class RegressionTests(unittest.TestCase):
    def test_future_grade_cannot_be_assumed(self):
        rules={'A':CourseRule('A',3,(),U,'synthetic'), 'B':CourseRule('B',3,((Alternative('A','B'),),),U,'synthetic')}
        with self.assertRaisesRegex(ScheduleError,'Future minimum-grade'):
            optimize_graph(rules,terms(2026,'Fall',2027,'Spring'),PlanningRequest(('A','B')))
    def test_known_completed_grade_allows(self):
        rules={'B':CourseRule('B',3,((Alternative('A','B'),),),U,'synthetic')}
        result=optimize_graph(rules,terms(2026,'Fall',2027,'Spring'),PlanningRequest(('B',),completed=('A',)),grades={'A':'A'})
        self.assertTrue(result['alternatives'])
if __name__=='__main__':unittest.main()
