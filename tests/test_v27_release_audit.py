import json
import pytest
from src.release_audit import audit_release
from server import plan

def test_missing_registry_fails_closed(tmp_path):
    r=audit_release(tmp_path/'missing.json')
    assert r['status']=='blocked' and r['graduation_planning_enabled'] is False

def test_forged_verified_registry_rejected(tmp_path):
    f=tmp_path/'registry.json'
    f.write_text(json.dumps({'catalog_year':'2026-2027','total_discovered':1,'programs':[{'id':'math','url':'https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/','plan_ready':True}]}))
    r=audit_release(f)
    assert any('Untrusted registry' in x for x in r['errors'])

def test_wrong_domain_rejected(tmp_path):
    f=tmp_path/'registry.json'
    f.write_text(json.dumps({'catalog_year':'2026-2027','total_discovered':1,'programs':[{'id':'math','url':'https://catalog.unc.edu.evil.com/undergraduate/programs-study/math/'}]}))
    assert any('Unexpected program source' in x for x in audit_release(f)['errors'])

@pytest.mark.parametrize('payload',[
 {'completed':'MATH 231'},
 {'required':'MATH 232'},
 {'maxCredits':True},
 {'maxCredits':0},
 {'locked':[]},
 {'grades':[]},
 {'summer':'false'},
 {'start':'Fall NaN'},
 {'completed':['MATH 231','MATH 231']},
])
def test_invalid_payloads_rejected(payload):
    with pytest.raises(ValueError):plan({'program':'mathematics-major-ba',**payload})
