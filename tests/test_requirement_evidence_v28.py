import unittest
from src.requirement_evidence import extract_rows

class EvidenceTests(unittest.TestCase):
    def test_rows_and_provenance(self):
        raw=b'<table><tr><th>Course</th><th>Hours</th></tr><tr><td>MATH 381</td><td>3</td></tr></table>'
        result=extract_rows(raw,'mathematics-major-ba','https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/')
        self.assertEqual(result['candidate_rows'][0]['course_codes'],['MATH 381'])
        self.assertEqual(result['approved_rules'],0)
    def test_ambiguity_not_approved(self):
        raw=b'<table><tr><td>Choose MATH 381 or STOR 215</td><td>3</td></tr></table>'
        result=extract_rows(raw,'math','https://catalog.unc.edu/')
        self.assertTrue(result['candidate_rows'][0]['needs_interpretation'])
        self.assertEqual(result['candidate_rows'][0]['review_status'],'unreviewed')
    def test_script_not_extracted(self):
        raw=b'<script><table><tr><td>MATH 999</td></tr></table></script><table><tr><td>MATH 231</td></tr></table>'
        result=extract_rows(raw,'math','https://catalog.unc.edu/')
        self.assertEqual(len(result['candidate_rows']),1)
    def test_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError):extract_rows(b'\xff','x','https://catalog.unc.edu/')
    def test_empty(self):
        self.assertEqual(extract_rows(b'<html></html>','x','https://catalog.unc.edu/') ['candidate_rows'],[])
if __name__=='__main__':unittest.main()
