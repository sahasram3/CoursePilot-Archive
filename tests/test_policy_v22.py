import unittest
from src.policy_v22 import audit
from src.unc_official_policy_2026 import CourseRecord

def c(code, credits=3, origin='unc', status='completed'):
    return CourseRecord(code,credits,origin,status)

class PolicyV22Tests(unittest.TestCase):
    def test_duplicates_do_not_inflate_credits(self):
        r=audit([c('MATH 231',4),c('MATH 231',4)])
        self.assertIn('duplicate_course:MATH 231',r['blockers'])
        self.assertEqual(r['total_projected_credits'],4)
    def test_future_courses_not_earned(self):
        r=audit([c('MATH 231',4,'unc','planned')])
        self.assertEqual(r['unc_earned_credits'],0)
        self.assertEqual(r['unc_projected_credits'],4)
    def test_half_exclusive_is_not_enough(self):
        programs={'A':{'kind':'major','core_courses':['A 1','A 2']},'B':{'kind':'minor','core_courses':['A 1','B 1']}}
        r=audit([c('A 1'),c('A 2'),c('B 1')],programs=programs,verified_mapping=True)
        self.assertIn('core_exclusivity_failed:A',r['blockers'])
        self.assertIn('core_exclusivity_failed:B',r['blockers'])
    def test_unverified_mapping_fails_closed(self):
        self.assertIn('program_mapping_unverified',audit([c('A 1')])['blockers'])
    def test_nan_gpa_rejected(self):
        self.assertIn('unc_gpa_invalid',audit([c('A 1')],unc_gpa=float('nan'))['blockers'])
    def test_unknown_origin_rejected(self):
        self.assertIn('unknown_course_origin',audit([c('A 1',origin='unknown')])['blockers'])
    def test_future_residency_not_counted_as_earned(self):
        r=audit([c('A 1',origin='unc',status='planned')])
        self.assertEqual(r['unc_earned_credits'],0)
    def test_no_certification_even_if_inputs_look_good(self):
        r=audit([c('A 1')],unc_gpa=3.5,cohort='Fall 2026',gen_ed_verified=True,verified_mapping=True)
        self.assertFalse(r['eligible']);self.assertFalse(r['degree_certified'])
    def test_bs_specific_minimum_unverified(self):
        self.assertIn('bs_specific_minimum_unverified',audit([c('A 1')],degree_type='BS')['blockers'])
    def test_bad_program_gpa_rejected(self):
        p={'P':{'kind':'minor','core_courses':['A 1']}}
        r=audit([c('A 1')],programs=p,program_gpas={'P':float('inf')})
        self.assertIn('program_core_gpa_invalid:P',r['blockers'])

if __name__=='__main__':unittest.main()
