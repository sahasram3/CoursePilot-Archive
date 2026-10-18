import unittest
import tempfile
from pathlib import Path
from src.review_pipeline import extract_evidence, build_review_queue

PROGRAM={'id':'biology-major-bs','name':'Biology Major, B.S.','kind':'major','url':'https://catalog.unc.edu/undergraduate/programs-study/biology-major-bs/'}
HTML='''<html><body><h1>Biology Major, B.S.</h1><p>2026–2027 Academic Catalog</p><h2>Requirements</h2><table><tr><th>Course</th><th>Credit Hours</th></tr><tr><td>DEMO 101</td><td>4</td></tr></table><p>Prerequisites and elective options require review. This is illustrative fixture content, not UNC data.</p></body></html>'''

class ReviewPipelineTests(unittest.TestCase):
    def test_extracts_tables_without_approval(self):
        e=extract_evidence(HTML,PROGRAM,captured_at='fixed')
        self.assertEqual(e['tables'][0][1],['DEMO 101','4'])
        self.assertTrue(e['catalog_year_visible'])
        self.assertFalse(e['plan_ready'])
        self.assertEqual(e['rule_records_approved'],0)
    def test_year_mismatch_flagged(self):
        e=extract_evidence(HTML.replace('2026–2027','2025–2026'),PROGRAM)
        self.assertIn('catalog_year_not_confirmed',e['review_flags'])
    def test_source_domain_rejected(self):
        with self.assertRaises(ValueError):extract_evidence(HTML,{**PROGRAM,'url':'https://unc.example.edu/fake'})
    def test_missing_files_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            q=build_review_queue({'programs':[PROGRAM]},d)
            self.assertEqual(q['sources_supplied'],0)
            self.assertEqual(q['programs'][0]['review_status'],'source_missing')
    def test_change_detection(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'biology-major-bs.html').write_text(HTML,encoding='utf-8')
            registry={'programs':[PROGRAM]}
            old=build_review_queue(registry,d,captured_at='fixed')
            Path(d,'biology-major-bs.html').write_text(HTML+'<!-- change -->',encoding='utf-8')
            new=build_review_queue(registry,d,old,captured_at='fixed')
            self.assertIn('source_changed_since_last_snapshot',new['programs'][0]['review_flags'])
    def test_same_source_no_change(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'biology-major-bs.html').write_text(HTML,encoding='utf-8')
            old=build_review_queue({'programs':[PROGRAM]},d)
            new=build_review_queue({'programs':[PROGRAM]},d,old)
            self.assertNotIn('source_changed_since_last_snapshot',new['programs'][0]['review_flags'])

if __name__=='__main__':unittest.main()
