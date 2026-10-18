"""Fail-closed human review of catalog-derived candidate requirements.

This module does NOT assert that an entire degree is reviewed when a few rows are approved.
No AI or heuristic may sign off on a requirement. Offline CLI; no public write API.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from .catalog_registry import write_registry_atomic

KINDS = {'ALL', 'ANY', 'AT_LEAST'}
COURSE_RE = re.compile(r'^[A-Z]{2,5} [0-9]{3}[A-Z]?$')


def _official(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.netloc == 'catalog.unc.edu' and p.path.startswith('/undergraduate/programs-study/')


def _candidate_id(program_id, source_sha256, index):
    return hashlib.sha256(f'{program_id}:{source_sha256}:{index}'.encode()).hexdigest()[:20]


def initialize(candidate_queue):
    programs = []
    for p in candidate_queue.get('programs', []):
        entries = []
        for i, c in enumerate(p.get('candidates', [])):
            entries.append({'candidate_id': _candidate_id(p['id'], p.get('source_sha256') or 'missing', i),
                            'candidate_index': i, 'evidence': c, 'decision': 'pending',
                            'review': None})
        programs.append({'id': p['id'], 'name': p['name'], 'url': p['url'],
                         'catalog_year': p.get('catalog_year_requested'),
                         'catalog_year_visible': p.get('catalog_year_not_confirmed') is not True and 'catalog_year_not_confirmed' not in p.get('warnings', []),
                         'source_sha256': p.get('source_sha256'),
                         'source_status': p.get('source_status'),
                         'requirements_complete': False, 'completion_review': None,
                         'candidates': entries})
    return {'schema_version': 1, 'programs': programs, 'notice': 'Pending candidates and partial approvals are not degree-certified.'}


def approve(state, program_id, candidate_id, *, reviewer, evidence_quote, kind, courses,
            count=None, rationale='', reviewed_at=None):
    """Require explicit human attestation, exact evidence quote and structural checks."""
    if not reviewer or not reviewer.strip() or reviewer.strip().lower() in {'ai', 'bot', 'auto', 'automated'}:
        raise ValueError('Named human reviewer required')
    program = next((p for p in state['programs'] if p['id'] == program_id), None)
    if program is None: raise ValueError('Unknown program')
    if not program['source_sha256'] or not program['catalog_year_visible'] or program['source_status'] == 'source_missing':
        raise ValueError('Verified source and visible catalog year required')
    if program['catalog_year'] != '2026-2027' or not _official(program['url']):
        raise ValueError('Catalog year or source URL is invalid')
    candidate = next((c for c in program['candidates'] if c['candidate_id'] == candidate_id), None)
    if candidate is None: raise ValueError('Unknown candidate')
    if candidate['decision'] != 'pending': raise ValueError('Candidate already decided')
    evidence = candidate['evidence']
    if evidence.get('source_sha256') != program['source_sha256']:
        raise ValueError('Candidate source fingerprint mismatch')
    original = ' | '.join(evidence['verbatim_cells']) if evidence.get('evidence_type') == 'table_row' else evidence.get('verbatim_text', '')
    if not evidence_quote or evidence_quote.strip() not in original:
        raise ValueError('Evidence quote must occur verbatim in the original candidate')
    if kind not in KINDS: raise ValueError('Invalid requirement type')
    if not isinstance(courses, list) or not courses or len(courses) != len(set(courses)) or any(not COURSE_RE.fullmatch(x) for x in courses):
        raise ValueError('Invalid course list')
    if not set(courses).issubset(set(evidence.get('course_codes', []))):
        raise ValueError('Courses not in cited candidate; use a separate documented manual exception review')
    expected = len(courses) if kind == 'ALL' else 1 if kind == 'ANY' else count
    if not isinstance(expected, int) or not 1 <= expected <= len(courses):
        raise ValueError('Invalid requirement count')
    if kind != 'AT_LEAST' and count not in (None, expected):
        raise ValueError('Count conflicts with requirement kind')
    if len(rationale.strip()) < 12: raise ValueError('Explain interpretation in rationale (12+ characters)')
    candidate['decision'] = 'approved'
    candidate['review'] = {'reviewer': reviewer.strip(), 'reviewed_at_utc': reviewed_at or datetime.now(timezone.utc).isoformat(),
                           'evidence_quote': evidence_quote.strip(), 'rationale': rationale.strip(),
                           'rule': {'id': candidate_id, 'kind': kind, 'courses': courses, 'count': expected,
                                    'source_url': program['url'], 'catalog_year': program['catalog_year'],
                                    'source_sha256': program['source_sha256'], 'verified': True}}
    return candidate['review']['rule']


def reject(state, program_id, candidate_id, *, reviewer, reason):
    if not reviewer.strip() or len(reason.strip()) < 12: raise ValueError('Human reviewer and rejection reason required')
    program = next((p for p in state['programs'] if p['id'] == program_id), None)
    if program is None: raise ValueError('Unknown program')
    candidate = next((c for c in program['candidates'] if c['candidate_id'] == candidate_id), None)
    if candidate is None or candidate['decision'] != 'pending': raise ValueError('Candidate not pending')
    candidate['decision'] = 'rejected'
    candidate['review'] = {'reviewer': reviewer.strip(), 'reason': reason.strip()}


def reconcile_sources(state, fresh_queue):
    """Invalidate approval whenever source hash, year, or page availability changes."""
    fresh = {p['id']: p for p in fresh_queue.get('programs', [])}
    stale = []
    for p in state['programs']:
        new = fresh.get(p['id'])
        if not new or new.get('source_sha256') != p['source_sha256'] or 'catalog_year_not_confirmed' in new.get('warnings', []):
            p['requirements_complete'] = False
            p['completion_review'] = None
            for c in p['candidates']:
                if c['decision'] == 'approved':
                    c['decision'] = 'stale'
                    stale.append(c['candidate_id'])
    return stale


def export_approved(state):
    programs = []
    for p in state['programs']:
        rules = [c['review']['rule'] for c in p['candidates'] if c['decision'] == 'approved']
        # Partial rules may be exported for audit, but never as a complete degree.
        programs.append({'id': p['id'], 'catalog_year': p['catalog_year'],
                         'source_url': p['url'], 'source_sha256': p['source_sha256'],
                         'rules': rules, 'verified_rule_count': len(rules),
                         'degree_plan_ready': False, 'requirements_complete': False,
                         'notice': 'Partial reviewed requirements only; no complete degree certification.'})
    return {'schema_version': 1, 'programs': programs, 'degree_plans_certified': 0}


def report(state):
    return [{'id': p['id'], 'pending': sum(c['decision'] == 'pending' for c in p['candidates']),
             'approved': sum(c['decision'] == 'approved' for c in p['candidates']),
             'rejected': sum(c['decision'] == 'rejected' for c in p['candidates']),
             'stale': sum(c['decision'] == 'stale' for c in p['candidates']),
             'degree_plan_ready': False} for p in state['programs']]


def main():
    parser = argparse.ArgumentParser(description='Local human review; no automatic approvals')
    sub = parser.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init'); init.add_argument('--candidates', required=True); init.add_argument('--output', required=True)
    show = sub.add_parser('report'); show.add_argument('--state', required=True)
    exp = sub.add_parser('export'); exp.add_argument('--state', required=True); exp.add_argument('--output', required=True)
    approval = sub.add_parser('approve')
    approval.add_argument('--state', required=True); approval.add_argument('--program', required=True)
    approval.add_argument('--candidate', required=True); approval.add_argument('--reviewer', required=True)
    approval.add_argument('--quote', required=True); approval.add_argument('--kind', choices=sorted(KINDS), required=True)
    approval.add_argument('--courses', nargs='+', required=True); approval.add_argument('--count', type=int)
    approval.add_argument('--rationale', required=True)
    args = parser.parse_args()
    if args.action == 'init':
        result = initialize(json.loads(Path(args.candidates).read_text()))
        write_registry_atomic(result, args.output)
        print(json.dumps(report(result), indent=2)); return
    state = json.loads(Path(args.state).read_text())
    if args.action == 'report': print(json.dumps(report(state), indent=2)); return
    if args.action == 'export': write_registry_atomic(export_approved(state), args.output); print(args.output); return
    rule = approve(state, args.program, args.candidate, reviewer=args.reviewer, evidence_quote=args.quote,
                   kind=args.kind, courses=args.courses, count=args.count, rationale=args.rationale)
    write_registry_atomic(state, args.state)
    print(json.dumps(rule, indent=2))

if __name__ == '__main__': main()
