import json
import tempfile
import unittest
from pathlib import Path
from src.catalog_batch import assess_page,batch_import

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.sources=self.root/'sources';self.sources.mkdir()
        self.out=self.root/'out';self.registry=self.root/'registry.json'
        self.p={'id':'test-major-ba','name':'Test Major, B.A.','kind':'major','url':'https://catalog.unc.edu/undergraduate/programs-study/test-major-ba/'}
        self.registry.write_text(json.dumps({'catalog_year':'2026-2027','programs':[self.p]}))
        self.html='<html><h1>Test Major, B.A.</h1><p>2026–2027 Academic Catalog</p><h2>Requirements</h2>'+('x'*300)+'</html>'
    def test_missing_strict_does_not_write(self):
        with self.assertRaises(ValueError):batch_import(self.registry,self.sources,self.out)
        self.assertFalse(self.out.exists())
    def test_valid_candidate_never_approved(self):
        (self.sources/'test-major-ba.html').write_text(self.html)
        r=batch_import(self.registry,self.sources,self.out)
        self.assertEqual(r['counts']['candidate'],1)
        self.assertEqual(r['reviewed_programs'],0)
        self.assertTrue((self.out/'batch_manifest.json').exists())
    def test_partial_reports_missing(self):
        r=batch_import(self.registry,self.sources,self.out,strict=False)
        self.assertEqual(r['counts']['missing'],1)
    def test_wrong_edition_rejected(self):
        (self.sources/'test-major-ba.html').write_text(self.html.replace('2026–2027','2025–2026'))
        with self.assertRaises(ValueError):batch_import(self.registry,self.sources,self.out)
    def test_traversal_rejected(self):
        self.p['id']='../outside';self.registry.write_text(json.dumps({'catalog_year':'2026-2027','programs':[self.p]}))
        with self.assertRaises(ValueError):batch_import(self.registry,self.sources,self.out,strict=False)
    def test_untrusted_url_rejected(self):
        self.p['url']='https://evil.example/undergraduate/programs-study/test-major-ba/'
        self.registry.write_text(json.dumps({'catalog_year':'2026-2027','programs':[self.p]}))
        with self.assertRaises(ValueError):batch_import(self.registry,self.sources,self.out,strict=False)
    def test_missing_requirements(self):
        status,_=assess_page(self.p,self.html.replace('Requirements','Overview'))
        self.assertEqual(status,'requirements_unconfirmed')
if __name__=='__main__':unittest.main()
