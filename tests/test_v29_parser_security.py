import unittest
from src.requirement_evidence import extract_rows
from src.catalog_registry import validate_selection

class ParserRegressionTests(unittest.TestCase):
    def test_nested_inline_tags_keep_course_code(self):
        r=extract_rows(b'<table><tr><td><a>MATH</a> <strong>381</strong></td></tr></table>', 'x','https://catalog.unc.edu/')
        self.assertEqual(r['candidate_rows'][0]['course_codes'],['MATH 381'])
    def test_nested_tables_not_conflated(self):
        raw=b'<table><tr><td>MATH 231<table><tr><td>STOR 215</td></tr></table></td></tr></table>'
        r=extract_rows(raw,'x','https://catalog.unc.edu/')
        self.assertEqual(len(r['candidate_rows']),2)
        self.assertEqual({tuple(x['course_codes']) for x in r['candidate_rows']},{('MATH 231',),('STOR 215',)})
    def test_simple_row_still_requires_interpretation(self):
        r=extract_rows(b'<table><tr><td>MATH 381</td></tr></table>','x','https://catalog.unc.edu/')
        self.assertTrue(r['candidate_rows'][0]['needs_interpretation'])
        self.assertFalse(r['candidate_rows'][0]['ambiguity_detected'])
    def test_template_excluded(self):
        r=extract_rows(b'<template><table><tr><td>MATH 999</td></tr></table></template><table><tr><td>MATH 231</td></tr></table>','x','https://catalog.unc.edu/')
        self.assertEqual(r['candidate_rows'][0]['course_codes'],['MATH 231'])
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):extract_rows(b'','x','https://catalog.unc.edu/')
    def test_malformed_selection_fails_as_validation_error(self):
        registry={'programs':[{'id':'math','kind':'major'}]}
        for pid in ([],{},None,7):
            with self.subTest(pid=pid):
                with self.assertRaises(ValueError):validate_selection([{'id':pid,'kind':'major'}],registry)
if __name__=='__main__':unittest.main()
