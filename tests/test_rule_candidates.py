import unittest
from src.rule_candidates import classify_row,extract_candidates,build_candidate_queue

BASE={'id':'demo-major','name':'DEMO','url':'https://catalog.unc.edu/undergraduate/programs-study/demo-major/',
'source_sha256':'hash','review_status':'needs_human_review','catalog_year_visible':True,
'catalog_year_requested':'2026-2027','tables':[[['Course','Credit Hours'],['DEMO 101','4'],
['DEMO 201 or DEMO 202','3'],['Three additional DEMO courses above 500','9'],
['DEMO 301','3–4']]],'evidence_excerpt':'A minimum grade of C is required. Prerequisite: DEMO 101. Students may not double count courses.'}
class CandidateTests(unittest.TestCase):
 def test_single_course(self):
  x=classify_row(['DEMO 101','4']);self.assertEqual(x['candidate_type'],'single_course_candidate');self.assertEqual(x['credit_hours_observed'],4)
 def test_choice_not_single(self):
  x=classify_row(['DEMO 201 or DEMO 202','3']);self.assertEqual(x['candidate_type'],'choice_or_group_candidate');self.assertEqual(len(x['course_codes']),2)
 def test_elective_not_single(self):
  self.assertNotEqual(classify_row(['Three additional DEMO courses above 500','9'])['candidate_type'],'single_course_candidate')
 def test_variable_credit_flag(self):
  x=classify_row(['DEMO 301','3–4']);self.assertIsNone(x['credit_hours_observed']);self.assertIn('variable_credit_range',x['review_flags'])
 def test_prose_candidates(self):
  x=extract_candidates(BASE);self.assertTrue(any(c['candidate_type']=='policy_text_candidate' for c in x['candidates']))
 def test_provenance(self):
  x=extract_candidates(BASE);self.assertEqual(x['candidates'][0]['source_sha256'],'hash');self.assertEqual(x['candidates'][0]['row_index'],1)
 def test_no_approval(self):
  x=extract_candidates(BASE);self.assertFalse(x['plan_ready']);self.assertEqual(x['approved_rules'],0)
 def test_missing_source(self):
  x=extract_candidates({'id':'x','name':'X','url':'https://catalog.unc.edu/undergraduate/programs-study/x/','review_status':'source_missing'});self.assertEqual(x['review_status'],'source_missing')
 def test_wrong_year(self):
  x=extract_candidates({**BASE,'catalog_year_visible':False});self.assertIn('catalog_year_not_confirmed',x['warnings'])
 def test_coverage(self):
  x=build_candidate_queue({'programs':[BASE,{'id':'x','name':'X','url':'https://catalog.unc.edu/undergraduate/programs-study/x/','review_status':'source_missing'}]});self.assertEqual(x['programs_discovered'],2);self.assertEqual(x['programs_with_candidates'],1);self.assertEqual(x['approved_for_planning'],0)
if __name__=='__main__':unittest.main()
