import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from src.trusted_policy_store import load_policy, TrustError, policy_availability
from src.degree_policy import audit_degree

class TrustedPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'policies').mkdir()
        self.policy={'id':'unc-undergrad','catalog_year':'2026-2027',
                     'source_url':'https://catalog.unc.edu/undergraduate/',
                     'source_fingerprint':'a'*64,'reviewer':'Test Reviewer',
                     'reviewed_at':'2026-10-17','status':'reviewed',
                     'min_total_credits':120,'min_resident_credits':45,
                     'max_shared_program_courses':0,'gen_ed_groups':[]}
    def deploy(self):
        raw=json.dumps(self.policy).encode()
        (self.root/'policies'/'unc-undergrad.json').write_bytes(raw)
        manifest={'schema_version':1,'catalog_year':'2026-2027','policies':{'unc-undergrad':{'sha256':hashlib.sha256(raw).hexdigest()}}}
        blob=json.dumps(manifest).encode()
        (self.root/'manifest.json').write_bytes(blob)
        return hashlib.sha256(blob).hexdigest()
    def test_missing_pin_denied(self):
        self.deploy()
        with self.assertRaises(TrustError):load_policy(self.root,'unc-undergrad')
    def test_reviewed_pinned_policy_loads(self):
        pin=self.deploy()
        self.assertEqual(load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin).min_total_credits,120)
    def test_tamper_policy_denied(self):
        pin=self.deploy()
        self.policy['min_total_credits']=1
        (self.root/'policies'/'unc-undergrad.json').write_text(json.dumps(self.policy))
        with self.assertRaisesRegex(TrustError,'integrity'):load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin)
    def test_tamper_manifest_denied(self):
        pin=self.deploy()
        (self.root/'manifest.json').write_text('{}')
        with self.assertRaisesRegex(TrustError,'integrity'):load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin)
    def test_path_traversal_denied(self):
        pin=self.deploy()
        for name in ('../manifest','/etc/passwd','unc-undergrad.json'):
            with self.subTest(name=name),self.assertRaises(TrustError):load_policy(self.root,name,pinned_manifest_sha256=pin)
    def test_unreviewed_denied_even_if_pinned(self):
        self.policy['status']='draft'
        pin=self.deploy()
        with self.assertRaises(TrustError):load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin)
    def test_missing_constraints_denied(self):
        self.policy['min_resident_credits']=None
        pin=self.deploy()
        with self.assertRaises(TrustError):load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin)
    def test_status_without_pin(self):
        self.assertFalse(policy_availability(self.root)['available'])
    def test_student_supplied_policy_cannot_enable_degree_endpoint(self):
        from server import plan
        with self.assertRaises(ValueError):
            plan({'program':'neuroscience-minor','policy':self.policy,'reviewed':True})
    def test_no_graduation_certification_even_when_audit_passes(self):
        pin=self.deploy()
        policy=load_policy(self.root,'unc-undergrad',pinned_manifest_sha256=pin)
        result=audit_degree(policy,completed=['A'],credits={'A':120},resident_courses=['A'],program_courses={'m':['A']},verified_program_mapping=True)
        self.assertTrue(result['eligible'])
        self.assertFalse(result['degree_certified'])

if __name__=='__main__':unittest.main()

class GateTests(unittest.TestCase):
    def test_degree_gate_blocks_even_if_client_claims_approval(self):
        from src.degree_plan_gate import check_degree_plan_request
        reg={'programs':[{'id':'math','kind':'major'}]}
        with tempfile.TemporaryDirectory() as d:
            result=check_degree_plan_request([{'id':'math','kind':'major','reviewed':True,'policy':{'status':'reviewed'}}],registry=reg,reviews={'programs':[]},checklists=[],trusted_policy_directory=d)
        self.assertFalse(result['eligible'])
        self.assertIn('trusted_university_policy_unavailable',result['blockers'])
        self.assertIn('complete_degree_solver_not_validated',result['blockers'])
    def test_unknown_program_rejected(self):
        from src.degree_plan_gate import check_degree_plan_request
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            check_degree_plan_request([{'id':'made-up','kind':'major'}],registry={'programs':[]},reviews={'programs':[]},checklists=[],trusted_policy_directory=d)
