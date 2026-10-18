import unittest
from src.planning_eligibility import evaluate_program, evaluate_combination, CAPABILITIES

class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.program={'id':'demo-major','catalog_year':'2026-2027','catalog_year_visible':True,
                      'source_sha256':'abc','source_status':'ok','candidates':[{'decision':'approved'}]}
        self.registry={'programs':[{'id':'demo-major','kind':'major'}, {'id':'demo-minor','kind':'minor'}]}
    def test_missing_checklist_blocks(self):
        result=evaluate_program(self.program,None)
        self.assertFalse(result['eligible'])
        self.assertIn('no_whole_program_checklist',result['blockers'])
    def test_unverified_rules_block(self):
        result=evaluate_program(self.program,None,course_rules={},required_courses=['DEMO 101'])
        self.assertIn('missing_reviewed_course:DEMO 101',result['blockers'])
    def test_empty_expansion_blocks(self):
        result=evaluate_program(self.program,None,course_rules={})
        self.assertIn('no_verified_full_requirement_expansion',result['blockers'])
    def test_incomplete_review_blocks(self):
        result=evaluate_program(self.program,{'categories':{}},course_rules={})
        self.assertIn('whole_program_review_incomplete',result['blockers'])
    def test_unimplemented_constraints_block_even_with_review(self):
        # Patch the human completeness assessor to isolate the planner gate.
        from unittest.mock import patch
        from src.whole_program import CATEGORIES
        checklist={'categories':{k:{'status':'verified'} for k in CATEGORIES}}
        with patch('src.planning_eligibility.assess',return_value={'internally_reviewed_for_planning':True,'blockers':[]}):
            result=evaluate_program(self.program,checklist,course_rules={'DEMO 101':type('R',(),{'status':'reviewed_course_description'})()},required_courses=['DEMO 101'])
        self.assertIn('unsupported_planner_constraint:double_counting',result['blockers'])
    def test_capabilities_are_conservative(self):
        self.assertFalse(CAPABILITIES['gen_ed_degree_wide'])
        self.assertFalse(CAPABILITIES['prerequisites_corequisites'])
    def test_missing_program_review_blocks_combination(self):
        result=evaluate_combination([{'id':'demo-major','kind':'major'}],self.registry,{'programs':[]},[])
        self.assertFalse(result['eligible'])
        self.assertIn('missing_program_review:demo-major',result['blockers'])
    def test_two_programs_require_compatibility_attestation(self):
        result=evaluate_combination([{'id':'demo-major','kind':'major'},{'id':'demo-minor','kind':'minor'}],self.registry,{'programs':[]},[])
        self.assertIn('combination_compatibility_not_human_verified',result['blockers'])
    def test_fake_boolean_compatibility_cannot_bypass(self):
        result=evaluate_combination([{'id':'demo-major','kind':'major'},{'id':'demo-minor','kind':'minor'}],self.registry,{'programs':[]},[],compatibility_attestation={'approved':True})
        self.assertFalse(result['eligible'])
    def test_invalid_combination_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_combination([{'id':'demo-minor','kind':'minor'}],self.registry,{'programs':[]},[])

if __name__=='__main__':unittest.main()
