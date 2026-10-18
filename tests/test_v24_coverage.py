import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.coverage_diagnostics import diagnostics, for_selection
from src.official_index_import import import_index

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.registry={'catalog_year':'2026-2027','programs':[
            {'id':'math-major-ba','name':'Math BA','kind':'major','url':'https://catalog.unc.edu/undergraduate/programs-study/math-major-ba/','plan_ready':True},
            {'id':'english-minor','name':'English Minor','kind':'minor','plan_ready':True}]}
    def test_untrusted_registry_cannot_claim_ready(self):
        d=diagnostics(self.registry)
        self.assertEqual(d['plan_ready'],0)
        self.assertFalse(d['programs'][0]['requirements_verified'])
    def test_source_html_does_not_grant_approval(self):
        with TemporaryDirectory() as tmp:
            Path(tmp,'math-major-ba.html').write_text('<html>test</html>')
            d=diagnostics(self.registry,tmp)
            self.assertTrue(d['programs'][0]['source_snapshot_available'])
            self.assertFalse(d['programs'][0]['plan_ready'])
    def test_duplicate_program_id_fails(self):
        self.registry['programs'].append(dict(self.registry['programs'][0]))
        with self.assertRaises(ValueError):diagnostics(self.registry)
    def test_path_traversal_fails(self):
        self.registry['programs'][0]['id']='../../bad'
        with self.assertRaises(ValueError):diagnostics(self.registry)
    def test_wrong_catalog_year_fails(self):
        self.registry['catalog_year']='2025-2026'
        with self.assertRaises(ValueError):diagnostics(self.registry)
    def test_valid_multi_program_selection_reports_missing_evidence(self):
        result=for_selection(self.registry,[{'id':'math-major-ba','kind':'major'}, {'id':'english-minor','kind':'minor'}])
        self.assertFalse(result['eligible'])
        self.assertEqual(len(result['programs']),2)
    def test_fake_approval_does_not_change_status(self):
        self.registry['programs'][0].update(requirements_status='approved',reviewer='fake',plan_ready=True)
        self.assertEqual(diagnostics(self.registry)['verified'],0)
    def test_short_import_fails(self):
        with self.assertRaises(ValueError):import_index('<html></html>',minimum=1)

if __name__=='__main__':unittest.main()
