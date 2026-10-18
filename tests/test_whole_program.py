import copy
import unittest
from src.approval_workflow import initialize, approve
from src.whole_program import CATEGORIES, create_checklist, assess, attest, coverage_report

URL='https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/'
HASH='f'*64

def fixture():
    queue={'programs':[{'id':'demo','name':'DEMO (synthetic)','url':URL,'catalog_year_requested':'2026-2027',
        'source_sha256':HASH,'source_status':'needs_human_review','warnings':[],
        'candidates':[{'evidence_type':'table_row','verbatim_cells':['MATH 231','4'],
                       'course_codes':['MATH 231'],'source_sha256':HASH}]}]}
    state=initialize(queue)
    p=state['programs'][0]
    c=p['candidates'][0]['candidate_id']
    approve(state,'demo',c,reviewer='Fixture Human',evidence_quote='MATH 231',kind='ALL',
            courses=['MATH 231'],rationale='Checked the source row for the fixture')
    return state,p

def decisions():
    return {key:{'status':'verified','notes':'Human inspected the relevant source section',
                 'evidence':'Source section A'} for key in CATEGORIES}

class WholeProgramTests(unittest.TestCase):
    def setUp(self): self.state,self.p=fixture(); self.check=create_checklist(self.p,source_sections=['Requirements','Footnotes'])
    def test_initial_blocked(self): self.assertFalse(assess(self.p,self.check)['internally_reviewed_for_planning'])
    def test_requires_all_sections(self):
        with self.assertRaises(ValueError): attest(self.p,self.check,reviewer='Human',section_ids=['Requirements'],category_decisions=decisions())
    def test_requires_every_category(self):
        d=decisions(); del d['residency']
        with self.assertRaises(ValueError): attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=d)
    def test_unresolved_rejected(self):
        d=decisions(); d['residency']['status']='unresolved'
        with self.assertRaises(ValueError): attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=d)
    def test_no_bot(self):
        with self.assertRaises(ValueError): attest(self.p,self.check,reviewer='bot',section_ids=['Requirements','Footnotes'],category_decisions=decisions())
    def test_attested_not_degree_certified(self):
        result=attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=decisions())
        self.assertTrue(result['internally_reviewed_for_planning']); self.assertFalse(result['degree_certified'])
    def test_stale_hash_blocks(self):
        attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=decisions())
        self.p['source_sha256']='a'*64
        self.assertIn('source_changed_or_missing',assess(self.p,self.check)['blockers'])
    def test_pending_candidate_blocks(self):
        self.p['candidates'].append({'decision':'pending'})
        with self.assertRaises(ValueError): attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=decisions())
    def test_coverage_missing_checklist(self):
        r=coverage_report(self.state,[])
        self.assertEqual(r['internally_reviewed_for_planning'],0)
    def test_coverage_after_attestation(self):
        attest(self.p,self.check,reviewer='Human',section_ids=['Requirements','Footnotes'],category_decisions=decisions())
        self.assertEqual(coverage_report(self.state,[self.check])['internally_reviewed_for_planning'],1)
    def test_no_candidates_blocks(self):
        self.p['candidates']=[]
        self.assertIn('no_candidate_evidence',assess(self.p,self.check)['blockers'])
    def test_invalid_source_sections(self):
        with self.assertRaises(ValueError): create_checklist(self.p,source_sections=[])

if __name__=='__main__': unittest.main()
