"""Conservative whole-program completeness review, not degree certification.

This module never infers completeness from number of approved course rows.
A human must attest to every category, including non-course restrictions.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from .catalog_registry import write_registry_atomic

CATEGORIES = (
    'required_courses', 'elective_groups', 'concentrations_tracks',
    'prerequisites_corequisites', 'minimum_grades_gpa', 'credit_totals',
    'gen_ed_degree_wide', 'residency', 'double_counting',
    'substitutions_transfer_ap_ib', 'admission_progression',
    'course_offerings', 'other_catalog_notes'
)
VALID = {'verified', 'not_applicable', 'unresolved'}


def create_checklist(program, *, source_sections):
    """source_sections: human-defined catalog headings/anchors, not parsed guesses."""
    if not program.get('id') or not program.get('source_sha256'):
        raise ValueError('Program and source fingerprint required')
    if not isinstance(source_sections, list) or not source_sections or any(not isinstance(s, str) or not s.strip() for s in source_sections):
        raise ValueError('List every relevant source section before completeness review')
    if len(source_sections) != len(set(source_sections)):
        raise ValueError('Duplicate source section')
    return {'program_id': program['id'], 'catalog_year': program['catalog_year'],
            'source_sha256': program['source_sha256'], 'source_sections': source_sections,
            'reviewed_sections': [], 'categories': {key: {'status': 'unresolved', 'notes': '', 'evidence': ''} for key in CATEGORIES},
            'reviewer': '', 'reviewed_at_utc': None, 'human_attested': False}


def assess(program, checklist):
    """Return blockers; never claim official graduation eligibility."""
    blockers = []
    if checklist.get('program_id') != program.get('id'): blockers.append('program_id_mismatch')
    if checklist.get('catalog_year') != program.get('catalog_year') or program.get('catalog_year') != '2026-2027': blockers.append('catalog_year_mismatch')
    if not program.get('catalog_year_visible'): blockers.append('catalog_year_not_confirmed')
    if not program.get('source_sha256') or checklist.get('source_sha256') != program.get('source_sha256'): blockers.append('source_changed_or_missing')
    if program.get('source_status') == 'source_missing': blockers.append('source_missing')
    candidates = program.get('candidates', [])
    if not candidates: blockers.append('no_candidate_evidence')
    if any(c.get('decision') in ('pending', 'stale') for c in candidates): blockers.append('unresolved_candidates')
    if not any(c.get('decision') == 'approved' for c in candidates): blockers.append('no_approved_rules')
    sections = checklist.get('source_sections', [])
    reviewed = checklist.get('reviewed_sections', [])
    if not sections or len(sections) != len(set(sections)) or set(sections) != set(reviewed) or len(reviewed) != len(set(reviewed)):
        blockers.append('source_sections_not_fully_reviewed')
    categories = checklist.get('categories', {})
    if set(categories) != set(CATEGORIES): blockers.append('missing_review_categories')
    for key in CATEGORIES:
        entry = categories.get(key, {})
        if entry.get('status') not in VALID or entry.get('status') == 'unresolved': blockers.append(f'unresolved:{key}')
        elif not entry.get('evidence', '').strip() or len(entry.get('notes', '').strip()) < 12:
            blockers.append(f'insufficient_evidence:{key}')
    if not checklist.get('human_attested') or not checklist.get('reviewer', '').strip() or not checklist.get('reviewed_at_utc'):
        blockers.append('human_completeness_attestation_missing')
    return {'program_id': program.get('id'), 'internally_reviewed_for_planning': not blockers,
            'degree_certified': False, 'blockers': blockers,
            'approved_rules': sum(c.get('decision') == 'approved' for c in candidates)}


def attest(program, checklist, *, reviewer, section_ids, category_decisions):
    """Local human-only attestation. Caller must actually inspect original sources."""
    if not reviewer or reviewer.strip().lower() in {'ai','bot','auto','automated'}:
        raise ValueError('Named human reviewer required')
    if set(category_decisions) != set(CATEGORIES): raise ValueError('Every category must be explicitly assessed')
    if set(section_ids) != set(checklist['source_sections']) or len(section_ids) != len(set(section_ids)):
        raise ValueError('Every source section must be checked')
    for key, value in category_decisions.items():
        if value.get('status') not in {'verified','not_applicable'}: raise ValueError('Cannot attest unresolved category: ' + key)
        if len(value.get('notes', '').strip()) < 12 or not value.get('evidence', '').strip():
            raise ValueError('Evidence and substantive notes required: ' + key)
    checklist.update({'reviewed_sections': list(section_ids), 'categories': category_decisions,
                      'reviewer': reviewer.strip(), 'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
                      'human_attested': True})
    result = assess(program, checklist)
    if not result['internally_reviewed_for_planning']:
        checklist['human_attested'] = False
        raise ValueError('Cannot attest incomplete program: ' + ', '.join(result['blockers']))
    return result


def coverage_report(review_state, checklists):
    by_id = {c['program_id']: c for c in checklists}
    rows = [assess(p, by_id[p['id']]) if p['id'] in by_id else
            {'program_id': p['id'], 'internally_reviewed_for_planning': False, 'degree_certified': False,
             'blockers': ['no_whole_program_checklist'], 'approved_rules': 0}
            for p in review_state.get('programs', [])]
    return {'catalog_year': '2026-2027', 'programs_in_review_queue': len(rows),
            'internally_reviewed_for_planning': sum(r['internally_reviewed_for_planning'] for r in rows),
            'degree_certified': 0, 'programs': rows}


def main():
    parser = argparse.ArgumentParser(description='Fail-closed whole-program coverage audit')
    parser.add_argument('--reviews', required=True)
    parser.add_argument('--checklists', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    state = json.loads(Path(args.reviews).read_text())
    checklists = json.loads(Path(args.checklists).read_text())
    report = coverage_report(state, checklists.get('checklists', []))
    write_registry_atomic(report, args.output)
    print(json.dumps({'total': report['programs_in_review_queue'], 'internally_reviewed_for_planning': report['internally_reviewed_for_planning']}, indent=2))

if __name__ == '__main__': main()
