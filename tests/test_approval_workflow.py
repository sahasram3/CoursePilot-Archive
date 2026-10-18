import copy
import unittest
from src.approval_workflow import initialize, approve, reject, reconcile_sources, export_approved, report

HASH = 'a' * 64
URL = 'https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/'

def queue():
    return {'programs': [{'id':'math-ba','name':'Mathematics BA','url':URL,
        'catalog_year_requested':'2026-2027','source_sha256':HASH,
        'source_status':'needs_human_review','warnings':[],
        'candidates':[{'candidate_type':'single_course_candidate','evidence_type':'table_row',
            'verbatim_cells':['MATH 231','4'],'course_codes':['MATH 231'], 'source_sha256':HASH}]}]}

def approval(state, **kwargs):
    c=state['programs'][0]['candidates'][0]['candidate_id']
    params=dict(reviewer='Sample Reviewer', evidence_quote='MATH 231',kind='ALL',
                courses=['MATH 231'],rationale='Confirmed exact row and course code')
    params.update(kwargs)
    return approve(state,'math-ba',c,**params)

class ApprovalTests(unittest.TestCase):
    def setUp(self): self.state=initialize(queue())
    def test_initial_unapproved(self):
        self.assertEqual(report(self.state)[0]['pending'],1)
        self.assertFalse(export_approved(self.state)['programs'][0]['degree_plan_ready'])
    def test_human_approval_export_still_not_degree_ready(self):
        rule=approval(self.state)
        self.assertEqual(rule['courses'],['MATH 231'])
        self.assertEqual(export_approved(self.state)['programs'][0]['verified_rule_count'],1)
        self.assertFalse(export_approved(self.state)['programs'][0]['degree_plan_ready'])
    def test_no_bot_reviewer(self):
        with self.assertRaises(ValueError): approval(self.state, reviewer='bot')
    def test_quote_must_be_verbatim(self):
        with self.assertRaises(ValueError): approval(self.state, evidence_quote='MATH 999')
    def test_no_fabricated_course(self):
        with self.assertRaises(ValueError): approval(self.state, courses=['MATH 999'])
    def test_no_missing_year(self):
        self.state['programs'][0]['catalog_year_visible']=False
        with self.assertRaises(ValueError): approval(self.state)
    def test_no_hash_mismatch(self):
        self.state['programs'][0]['source_sha256']='b'*64
        with self.assertRaises(ValueError): approval(self.state)
    def test_no_duplicate_approval(self):
        approval(self.state)
        with self.assertRaises(ValueError): approval(self.state)
    def test_invalid_requirement_count(self):
        with self.assertRaises(ValueError): approval(self.state, kind='AT_LEAST',count=2)
    def test_source_change_stales_approval(self):
        approval(self.state)
        changed=copy.deepcopy(queue()); changed['programs'][0]['source_sha256']='b'*64
        stale=reconcile_sources(self.state,changed)
        self.assertEqual(len(stale),1)
        self.assertEqual(export_approved(self.state)['programs'][0]['verified_rule_count'],0)
    def test_source_missing_stales_approval(self):
        approval(self.state)
        self.assertEqual(len(reconcile_sources(self.state,{'programs':[]})),1)
    def test_reject_with_reason(self):
        c=self.state['programs'][0]['candidates'][0]['candidate_id']
        reject(self.state,'math-ba',c,reviewer='Sample Reviewer',reason='Table header not an actual requirement')
        self.assertEqual(report(self.state)[0]['rejected'],1)

if __name__=='__main__': unittest.main()
