import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.catalog_registry import ingest_html, read_registry, write_registry_atomic, validate_selection

HTML='''<a href="/undergraduate/programs-study/math-major-ba/">Mathematics Major BA</a><a href="/undergraduate/programs-study/economics-major-bs/">Economics Major BS</a><a href="/undergraduate/programs-study/neuroscience-minor/">Neuroscience Minor</a><a href="/undergraduate/programs-study/data-science-minor/">Data Science Minor</a>'''
class RegistryTests(unittest.TestCase):
 def setUp(self):self.registry=ingest_html(HTML,minimum=4)
 def test_discovery(self):self.assertEqual(self.registry['total_discovered'],4)
 def test_reject_partial(self):
  with self.assertRaises(ValueError):ingest_html(HTML,minimum=100)
 def test_atomic_roundtrip(self):
  with TemporaryDirectory() as d:
   p=Path(d)/'registry.json';write_registry_atomic(self.registry,p)
   self.assertEqual(read_registry(p)['total_discovered'],4)
 def test_legal_combinations(self):
  for items in [[('math-major-ba','major')],[('math-major-ba','major'),('economics-major-bs','major'),('neuroscience-minor','minor')],[('math-major-ba','major'),('neuroscience-minor','minor'),('data-science-minor','minor')]]:
   self.assertTrue(validate_selection([{'id':a,'kind':b} for a,b in items],self.registry)['valid_combination'])
 def test_no_three_minors(self):
  with self.assertRaises(ValueError):validate_selection([{'id':'neuroscience-minor','kind':'minor'}]*3,self.registry)
 def test_no_duplicates(self):
  with self.assertRaises(ValueError):validate_selection([{'id':'math-major-ba','kind':'major'}]*2,self.registry)
 def test_unknown_rejected(self):
  with self.assertRaises(ValueError):validate_selection([{'id':'fake-major','kind':'major'}],self.registry)
 def test_kind_mismatch(self):
  with self.assertRaises(ValueError):validate_selection([{'id':'math-major-ba','kind':'minor'}],self.registry)
if __name__=='__main__':unittest.main()
