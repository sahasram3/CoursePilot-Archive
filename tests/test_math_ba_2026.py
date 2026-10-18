import unittest
from src.math_ba_2026 import audit_math_ba,source_record
class MathBAEvidenceTests(unittest.TestCase):
 def test_catalog_year(self):self.assertEqual(source_record()['catalog_year'],'2026-2027')
 def test_major_hours(self):self.assertEqual(source_record()['hours'],33)
 def test_credits(self):self.assertEqual(source_record()['fixed_course_credits']['MATH 231'],4)
 def test_381_substitution_only_with_statistics(self):
  x={'MATH 231','MATH 232','MATH 383','MATH 521','STOR 215','MATH 233','MATH 347'}
  self.assertIn('MATH 381',audit_math_ba(x).missing)
  self.assertNotIn('MATH 381',audit_math_ba(x,statistics_major=True).missing)
 def test_521_not_counted_as_additional(self):self.assertNotIn('MATH 521',audit_math_ba({'MATH 521','MATH 522'}).upper_level_completed)
 def test_never_certify_full_degree(self):self.assertFalse(audit_math_ba({'MATH 231','MATH 232','MATH 233','MATH 347','MATH 381','MATH 383','MATH 521','MATH 522','MATH 524','MATH 535'}).major_complete)
if __name__=='__main__':unittest.main()
