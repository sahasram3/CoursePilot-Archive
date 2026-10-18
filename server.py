"""PreReqPath local demo server: stdlib only, no accounts or external data sharing."""
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from src.planner import terms
from src.release_audit import audit_release
from src.coverage_diagnostics import diagnostics, for_selection
from src.catalog_registry import read_registry, validate_selection
from src.graph_optimizer import PlanningRequest, optimize_graph, ScheduleError
from src.roadmap_audit import audit_roadmap
from src.math_prerequisites_2026 import RULES
from src.planning_eligibility import evaluate_combination
from src.trusted_policy_store import policy_availability
from src.degree_plan_gate import check_degree_plan_request
from src.policy_v22 import audit as audit_official_provisional
from src.unc_official_policy_2026 import CourseRecord
import os

ROOT=Path(__file__).parent/'web'
REGISTRY_FILE=Path(__file__).parent/'data'/'unc_program_registry.json'

def all_programs():
    registry=read_registry(REGISTRY_FILE)
    if registry['programs']:
        return registry
    return {'catalog_year':'2026-2027','programs':[{'id':p['id'],'name':p['name'],'kind':p['kind'],'url':'https://catalog.unc.edu/undergraduate/programs-study/','requirements_status':'unreviewed','plan_ready':False} for p in DEMO_PROGRAMS], 'total_discovered':0,'verification_notice':'Live UNC program index not imported; only three illustrative entries are shown.'}

DEMO_REQUIRED=('MATH 232','MATH 233','MATH 381','MATH 383','MATH 521','MATH 523')
DEMO_PROGRAMS=[
 {'id':'mathematics-major-ba','name':'Mathematics Major, B.A.','kind':'major','status':'partial','note':'Reviewed subset of course prerequisites; NOT a complete degree plan'},
 {'id':'statistics-analytics-major-bs','name':'Statistics and Analytics Major, B.S.','kind':'major','status':'unverified','note':'Program source identified; requirements not approved'},
 {'id':'neuroscience-minor','name':'Neuroscience Minor','kind':'minor','status':'unverified','note':'Program source identified; requirements not approved'},
]

def plan(payload):
    program=payload.get('program')
    if program!='mathematics-major-ba':
        raise ValueError('This program has not been verified for planning. No schedule was generated.')
    start=payload.get('start','Fall 2026').split()
    end=payload.get('graduation','Spring 2029').split()
    if len(start)!=2 or len(end)!=2 or start[0] not in ('Fall','Spring') or end[0] not in ('Fall','Spring'):
        raise ValueError('Choose valid start and graduation terms')
    if not (start[1].isdigit() and end[1].isdigit() and 2020<=int(start[1])<=2045 and 2020<=int(end[1])<=2045): raise ValueError('Invalid academic year')
    if not isinstance(payload.get('summer',False),bool): raise ValueError('Summer must be true or false')
    calendar=terms(int(start[1]),start[0],int(end[1]),end[0],payload.get('summer',False))
    if len(calendar)>20: raise ValueError('Please select a horizon of at most 20 terms')
    if not isinstance(payload.get('completed',[]),list): raise ValueError('Completed courses must be a list')
    completed=tuple(payload.get('completed',[]))
    if len(completed)>150 or any(not isinstance(x,str) for x in completed): raise ValueError('Invalid completed courses')
    if not isinstance(payload.get('required',list(DEMO_REQUIRED)),list): raise ValueError('Required courses must be a list')
    required=tuple(payload.get('required',list(DEMO_REQUIRED)))
    if not required or len(required)>18 or any(c not in DEMO_REQUIRED for c in required):
        raise ValueError('Choose only the explicitly supported demonstration courses')
    locked=payload.get('locked',{})
    if not isinstance(locked,dict) or len(locked)>18 or any(not isinstance(k,str) or not isinstance(v,str) for k,v in locked.items()): raise ValueError('Invalid locked courses')
    max_credits=payload.get('maxCredits',18)
    if isinstance(max_credits,bool) or not isinstance(max_credits,int) or not 1<=max_credits<=24: raise ValueError('Credits must be an integer between 1 and 24')
    if len(set(completed))!=len(completed) or len(set(required))!=len(required): raise ValueError('Duplicate course entries')
    if not isinstance(payload.get('grades',{}),dict): raise ValueError('Grades must be an object')
    request=PlanningRequest(required=required,completed=completed,max_credits=max_credits,min_credits=0,locked=tuple(locked.items()))
    result=audit_roadmap(RULES,calendar,request,grades=payload.get('grades',{}),limit=3)
    # Supplemental university-wide policy audit uses only server-owned catalog credit
    # values. Completion origin and cohort are unknown unless independently verified.
    # Never treat student-supplied origin, reviewer, or certification flags as trusted.
    for alternative in result.get('alternatives', []):
        future={code for codes in alternative['terms'].values() for code in codes}
        codes=set(completed)|future
        records=[CourseRecord(code,RULES[code].credits,'unknown',
                              'completed' if code in completed else 'planned')
                 for code in sorted(codes) if code in RULES]
        alternative['official_policy_audit']=audit_official_provisional(
            records,degree_type='BA',cohort=None,verified_mapping=False,
            gen_ed_verified=False)
    result['official_policy_audit_notice']='All origin, cohort, and program mappings remain unverified; policy audit is provisional and cannot certify graduation.'
    result['scope']='Only six selected Math courses; degree-wide audit is blocked without a reviewed UNC policy. not a complete Mathematics B.A. or graduation audit'
    result['program']='Mathematics Major, B.A.'
    return result

class Handler(BaseHTTPRequestHandler):
    def respond(self,code,data):
        raw=json.dumps(data).encode()
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/programs':
            registry=all_programs()
            return self.respond(200,{'programs':[{**p,'status':('partial' if p['id']=='mathematics-major-ba' else 'unverified'), 'note':('Only a six-course demo, not a degree audit' if p['id']=='mathematics-major-ba' else 'Catalog listing only; no verified degree requirements')} for p in registry['programs']], 'total_discovered':registry['total_discovered'], 'scope':registry['verification_notice']})
        if path=='/api/planning-eligibility':
            registry=all_programs()
            return self.respond(200,{'policy_store':policy_availability(Path(__file__).parent/'trusted_policies',pinned_manifest_sha256=os.environ.get('PREREQPATH_TRUSTED_MANIFEST_SHA256')), 'eligible_programs':0,'programs_discovered':registry['total_discovered'],'notice':'No fully reviewed program rules or complete degree solver available. Real degree planning is disabled; the Math demo is separate.'})
        if path=='/api/coverage-detail':
            return self.respond(200,diagnostics(all_programs(),Path(__file__).parent/'saved_program_pages'))
        if path=='/api/release-audit':
            return self.respond(200,audit_release(REGISTRY_FILE, Path(__file__).parent/'saved_program_pages' if (Path(__file__).parent/'saved_program_pages'/'batch_manifest.json').exists() else None))
        if path=='/api/coverage':
            registry=all_programs()
            return self.respond(200,{'discovered':registry['total_discovered'],'plan_ready':0,'catalog_year':'2026-2027','notice':registry['verification_notice']})
        if path=='/api/policy-status':return self.respond(200,{'catalog_year':'2026-2027','policy_module':'v22','source':'https://catalog.unc.edu/undergraduate/degree-requirements/','independent_review':False,'real_degree_planning_enabled':False,'notice':'Source-backed provisional rules; not independently approved or complete.'})
        if path=='/api/courses':return self.respond(200,{'courses':[{'code':c,'credits':RULES[c].credits,'source':RULES[c].source_url} for c in DEMO_REQUIRED]})
        if path not in ('/','/app.js','/style.css'):return self.send_error(404)
        name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
        content=(ROOT/name).read_bytes();mime='text/html' if name.endswith('.html') else ('text/javascript' if name.endswith('.js') else 'text/css')
        self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def do_POST(self):
        if urlparse(self.path).path not in ('/api/plan','/api/validate-selection','/api/degree-plan'):return self.send_error(404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>30000:raise ValueError('Invalid request size')
            payload=json.loads(self.rfile.read(size))
            if not isinstance(payload,dict):raise ValueError('Expected a JSON object')
            if urlparse(self.path).path=='/api/degree-plan':
                selections=payload.get('programs',[])
                detail=for_selection(all_programs(),selections,Path(__file__).parent/'saved_program_pages')
                eligibility=check_degree_plan_request(selections,registry=all_programs(),reviews={'programs':[]},checklists=[],trusted_policy_directory=Path(__file__).parent/'trusted_policies',manifest_pin=os.environ.get('PREREQPATH_TRUSTED_MANIFEST_SHA256'))
                return self.respond(422,{'error':'Verified degree requirements are not yet available for the selected programs','eligibility':eligibility,'coverage':detail})
            if urlparse(self.path).path=='/api/validate-selection':
                return self.respond(200,validate_selection(payload.get('programs'),all_programs()))
            self.respond(200,plan(payload))
        except (ValueError,TypeError,KeyError,ScheduleError,OverflowError) as e:self.respond(422,{'error':str(e)})
    def log_message(self,format,*args):pass

if __name__=='__main__':
    print('Open http://127.0.0.1:8765')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
