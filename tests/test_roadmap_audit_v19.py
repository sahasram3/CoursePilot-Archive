import unittest
from src.roadmap_audit import audit_roadmap
from src.degree_policy import Policy, audit_degree
from src.graph_optimizer import PlanningRequest
from src.prerequisite_graph import CourseRule, Alternative
from src.planner import terms
U='https://catalog.unc.edu/courses/math/'
class RoadmapAuditTests(unittest.TestCase):
    def rules(self):
        return {'A':CourseRule('A',3,(),U,'synthetic'), 'B':CourseRule('B',3,((Alternative('A'),),),U,'synthetic')}
    def policy(self, **kw):
        x=dict(catalog_year='2026-2027',source_url=U,reviewer='Synthetic test reviewer',min_total_credits=6,max_shared_program_courses=0,min_resident_credits=3,status='reviewed')
        x.update(kw);return Policy(**x)
    def test_provisional_audit_blocked_without_policy(self):
        r=audit_roadmap(self.rules(),terms(2026,'Fall',2027,'Spring'),PlanningRequest(('A','B')))
        self.assertTrue(r['alternatives'])
        for plan in r['alternatives']:
            self.assertIn('independent_policy_review_pending',plan['degree_audit']['blockers'])
            self.assertFalse(plan['degree_ready'])
        self.assertFalse(r['degree_certified'])
    def test_policy_audit_applied_to_every_alternative(self):
        r=audit_roadmap(self.rules(),terms(2026,'Fall',2027,'Spring'),PlanningRequest(('A','B')),
                        policy=self.policy(),program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertTrue(r['alternatives'])
        self.assertTrue(all('legacy_policy_not_authoritative' in p['degree_audit']['blockers'] for p in r['alternatives']))
    def test_future_courses_not_residency(self):
        a=audit_degree(self.policy(),planned=('A','B'),credits={'A':3,'B':3},resident_courses=('A','B'),program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertIn('resident_course_not_completed_at_unc',a['blockers'])
        self.assertIn('insufficient_resident_credits',a['blockers'])
    def test_completed_residency_can_count(self):
        a=audit_degree(self.policy(),completed=('A',),planned=('B',),credits={'A':3,'B':3},resident_courses=('A',),program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertTrue(a['eligible'],a)
    def test_unknown_credit_blocks(self):
        a=audit_degree(self.policy(),completed=('A',),planned=('B',),credits={'A':3},resident_courses=('A',),program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertIn('missing_verified_credits:B',a['blockers'])
    def test_no_graduation_certification_even_when_policy_passes(self):
        r=audit_roadmap(self.rules(),terms(2026,'Fall',2027,'Spring'),PlanningRequest(('B',),completed=('A',)),
                        policy=self.policy(),program_courses={'major':['A','B']},verified_program_mapping=True,resident_completed=('A',),credits={'A':3,'B':3})
        self.assertTrue(r['alternatives'])
        self.assertFalse(r['alternatives'][0]['degree_audit']['eligible'])
        self.assertFalse(r['alternatives'][0]['degree_ready'])
if __name__=='__main__':unittest.main()
