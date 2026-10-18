import unittest
from src.catalog_pipeline import parse_index,parse_page
class CatalogPipelineTests(unittest.TestCase):
 def test_index_filters_and_deduplicates(self):
  html='<a href="/undergraduate/programs-study/mathematics-major-ba/">Math BA</a><a href="/undergraduate/programs-study/mathematics-major-ba/">Math BA</a><a href="/undergraduate/programs-study/neuroscience-minor/">Neuro minor</a><a href="/undergraduate/">Other</a>'
  p=parse_index(html);self.assertEqual(len(p),2);self.assertEqual({x['kind'] for x in p},{'major','minor'})
 def test_extract_does_not_certify(self):
  x=parse_page('<h1>Mathematics</h1><table><tr><td>MATH 231</td><td>4</td></tr></table>','https://catalog.unc.edu/test/')
  self.assertEqual(x['review_status'],'needs_human_review');self.assertEqual(x['tables'][0][0],['MATH 231','4'])
if __name__=='__main__':unittest.main()
