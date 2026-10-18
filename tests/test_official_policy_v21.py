import unittest
from src.unc_official_policy_2026 import CourseRecord, audit_official_facts, FACTS

class OfficialPolicyTests(unittest.TestCase):
    def test_thresholds_source_backed(self):
        self.assertEqual(FACTS['min_graduation_credits']['value'],120)
        self.assertEqual(FACTS['min_unc_credits']['value'],45)
    def test_future_courses_not_earned(self):
        r=audit_official_facts([CourseRecord('MATH 231',4,'unc','planned')],degree_type='BA',unc_gpa=3)
        self.assertEqual(r['unc_earned_credits'],0)
        self.assertEqual(r['unc_projected_credits'],4)
    def test_strict_exclusivity_courses_and_credits(self):
        codes=['DEMO 101','DEMO 102','DEMO 103','DEMO 104']
        courses=[CourseRecord(c,3,'unc') for c in codes]
        programs={'A':{'kind':'major','core_courses':codes[:3]},'B':{'kind':'minor','core_courses':codes[1:]}}
        r=audit_official_facts(courses,degree_type='BA',unc_gpa=3,programs=programs)
        self.assertIn('exclusive_core_majority_not_met:A',r['blockers'])
    def test_major_half_courses_and_credits(self):
        cs=[CourseRecord('DEMO 101',1,'unc'),CourseRecord('DEMO 102',4,'transfer'),CourseRecord('DEMO 103',4,'transfer')]
        r=audit_official_facts(cs,degree_type='BA',unc_gpa=3,programs={'X':{'kind':'major','core_courses':[c.code for c in cs]}})
        self.assertIn('major_half_core_at_unc_not_met:X',r['blockers'])
    def test_minor_nine_hours(self):
        cs=[CourseRecord('DEMO 101',3,'unc'),CourseRecord('DEMO 102',3,'unc'),CourseRecord('DEMO 103',3,'transfer')]
        r=audit_official_facts(cs,degree_type='BA',unc_gpa=3,programs={'X':{'kind':'minor','core_courses':[c.code for c in cs]}})
        self.assertIn('minor_nine_unc_core_hours_not_met:X',r['blockers'])
    def test_duplicate_credit_cannot_inflate(self):
        c=CourseRecord('DEMO 101',3,'unc')
        r=audit_official_facts([c,c],degree_type='BA',unc_gpa=3)
        self.assertEqual(r['planned_plus_earned_credits'],3)
        self.assertIn('duplicate_course_record:DEMO 101',r['blockers'])
    def test_conflicting_duplicate(self):
        r=audit_official_facts([CourseRecord('DEMO 101',3,'unc'),CourseRecord('DEMO 101',4,'transfer')],degree_type='BA',unc_gpa=3)
        self.assertIn('conflicting_duplicate_course:DEMO 101',r['blockers'])
    def test_gpa_unknown_is_not_pass(self):
        r=audit_official_facts([],degree_type='BA')
        self.assertIn('unc_cumulative_gpa_unknown',r['blockers'])
    def test_bs_minimum_requires_program(self):
        r=audit_official_facts([],degree_type='BS',unc_gpa=3)
        self.assertIn('bs_program_specific_credit_minimum_not_verified',r['blockers'])
    def test_future_grades_cannot_certify(self):
        r=audit_official_facts([],degree_type='BA',unc_gpa=4)
        self.assertFalse(r['degree_certified'])
    def test_unknown_origin(self):
        r=audit_official_facts([CourseRecord('DEMO 101',3,'unknown')],degree_type='BA',unc_gpa=3)
        self.assertIn('unknown_course_origin',r['blockers'])
    def test_2025_cohort_not_2026(self):
        r=audit_official_facts([],degree_type='BA',unc_gpa=3,catalog_year='2025-2026')
        self.assertIn('catalog_year_not_supported',r['blockers'])

if __name__=='__main__': unittest.main()
