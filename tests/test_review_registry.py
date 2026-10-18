import unittest
from src.review_registry import stage,approve,can_schedule

URL='https://catalog.unc.edu/undergraduate/programs-study/neuroscience-minor/'
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.e=stage('n1','Neuroscience Minor','NSCI 175 listed as core',URL,'NSCI 175 Introduction to Neuroscience')
    def test_staged_is_not_schedulable(self):
        self.assertFalse(can_schedule(self.e))
    def test_wrong_edition_fails(self):
        with self.assertRaises(ValueError):approve(self.e,'Reviewer','2025-2026',True)
    def test_unchecked_fails(self):
        with self.assertRaises(ValueError):approve(self.e,'Reviewer','2026-2027',False)
    def test_verified_has_audit_trail(self):
        v=approve(self.e,'Reviewer','2026-2027',True)
        self.assertTrue(can_schedule(v));self.assertTrue(v.reviewed_utc)
    def test_non_unc_source_fails(self):
        with self.assertRaises(ValueError):stage('a','x','claim','https://evil.example/a','text')
if __name__=='__main__':unittest.main()
