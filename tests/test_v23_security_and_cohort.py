import unittest
from src.cohort_gen_ed import route_gen_ed,audit_gen_ed
from src.authoritative_audit import audit_roadmap_policy
from src.roadmap_audit import audit_roadmap
from src.degree_policy import Policy
from src.graph_optimizer import PlanningRequest
from src.prerequisite_graph import CourseRule
from src.planner import terms
U='https://catalog.unc.edu/courses/math/'
class NewPolicyTests(unittest.TestCase):
    def test_missing_cohort(self):
        self.assertIn('entering_cohort_missing',route_gen_ed().blockers)
    def test_older_cohort_not_assumed_current(self):
        self.assertIn('archived_cohort_requirements_needed',route_gen_ed(entering_term='Fall 2025').blockers)
    def test_new_cohort_still_unverified(self):
        r=route_gen_ed(entering_term='Fall 2026')
        self.assertEqual(r.curriculum,'IDEAs in Action')
        self.assertFalse(r.approved_for_planning)
    def test_transfer_requires_review(self):
        self.assertIn('transfer_gen_ed_applicability_requires_review',route_gen_ed(entering_term='Fall 2026',transfer=True).blockers)
    def test_client_attributes_do_not_approve(self):
        self.assertFalse(audit_gen_ed(entering_term='Fall 2026',course_attributes={'MATH 231':['QR']})['eligible'])
    def test_course_double_count_block(self):
        r=audit_roadmap_policy(completed=['A'],planned=['A'],verified_credits={'A':3})
        self.assertIn('course_both_completed_and_planned',r['blockers'])
    def test_unknown_credits_block(self):
        r=audit_roadmap_policy(completed=['A'],planned=['B'],verified_credits={'A':3})
        self.assertIn('missing_verified_credit:B',r['blockers'])
    def test_legacy_policy_cannot_approve_roadmap(self):
        policy=Policy(catalog_year='2026-2027',source_url=U,reviewer='test',min_total_credits=3,max_shared_program_courses=0,min_resident_credits=0,status='reviewed')
        rules={'A':CourseRule('A',3,(),U,'synthetic')}
        result=audit_roadmap(rules,terms(2026,'Fall',2026,'Fall'),PlanningRequest(('A',)),policy=policy)
        self.assertIn('legacy_policy_not_authoritative',result['alternatives'][0]['degree_audit']['blockers'])
        self.assertFalse(result['alternatives'][0]['degree_audit']['eligible'])
    def test_legacy_policy_not_used_for_overlap(self):
        r=audit_roadmap_policy(completed=['A'],planned=[],verified_credits={'A':3},origins={'A':'unc'})
        self.assertEqual(r['policy_engine'],'authoritative_v23')
        self.assertFalse(r['degree_certified'])
if __name__=='__main__':unittest.main()
