import unittest
from src.degree_policy import Policy, PolicyError, audit_degree

class PolicyTests(unittest.TestCase):
    def policy(self, **kw):
        data=dict(catalog_year='2026-2027',source_url='https://catalog.unc.edu/undergraduate/',reviewer='Test reviewer',min_total_credits=9,gen_ed_groups=(('writing',('W1','W2'),1),),max_shared_program_courses=0,min_resident_credits=6,status='reviewed')
        data.update(kw)
        return Policy(**data)
    def test_credit_union_no_double_count(self):
        a=audit_degree(self.policy(),completed=['A','W1'],planned=['A','B'],credits={'A':3,'W1':3,'B':3},resident_courses=['A','W1'],program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertTrue(a['eligible'],a)
        self.assertEqual(a['unique_credits'],9)
    def test_unknown_credit_blocks(self):
        a=audit_degree(self.policy(),completed=['A','W1'],planned=['B'],credits={'A':3,'W1':3},resident_courses=['A','B'],program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertFalse(a['eligible'])
        self.assertIn('missing_verified_credits:B',a['blockers'])
    def test_missing_gen_ed(self):
        a=audit_degree(self.policy(),planned=['A','B','C'],credits=dict.fromkeys('ABC',3),resident_courses=['A','B'],program_courses={'major':['A','B']},verified_program_mapping=True)
        self.assertIn('gen_ed_unsatisfied:writing',a['blockers'])
    def test_double_count(self):
        a=audit_degree(self.policy(),planned=['A','B','W1'],credits={'A':3,'B':3,'W1':3},resident_courses=['A','B'],program_courses={'major':['A'],'minor':['A','B']},verified_program_mapping=True)
        self.assertIn('program_overlap_exceeds_reviewed_limit',a['blockers'])
    def test_missing_mapping_blocks(self):
        a=audit_degree(self.policy(),planned=['A','B','W1'],credits={'A':3,'B':3,'W1':3},resident_courses=['A','B'])
        self.assertIn('program_course_mapping_not_verified',a['blockers'])
    def test_unreviewed_policy_blocks(self):
        self.assertFalse(audit_degree(self.policy(status='draft'),planned=['A'])['eligible'])
    def test_residency_blocks(self):
        a=audit_degree(self.policy(),planned=['A','B','W1'],credits={'A':3,'B':3,'W1':3},resident_courses=['A'],program_courses={'major':['A']},verified_program_mapping=True)
        self.assertIn('insufficient_resident_credits',a['blockers'])
    def test_invalid_policy(self):
        with self.assertRaises(PolicyError): self.policy(min_total_credits=-1)
    def test_boolean_credit_rejected(self):
        a=audit_degree(self.policy(),planned=['A','B','W1'],credits={'A':True,'B':3,'W1':3})
        self.assertIn('missing_verified_credits:A',a['blockers'])
if __name__=='__main__': unittest.main()
