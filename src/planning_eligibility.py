"""Fail-closed eligibility gate for real degree planning.

A reviewed catalog program alone is insufficient: every relevant academic
constraint must be represented AND supported by the planner. This gate does
not grant UNC graduation certification.
"""
from .whole_program import assess, CATEGORIES

# Planner implementation capabilities. A category may be marked not applicable
# ONLY by an independently attested human checklist, not inferred here.
CAPABILITIES = {
    'required_courses': True,
    'elective_groups': False,  # arbitrary nested electives not integrated with graph optimizer
    'concentrations_tracks': False,
    'prerequisites_corequisites': False,  # corequisites and all exception types unsupported
    'minimum_grades_gpa': False,  # program GPA and repeat rules unsupported
    'credit_totals': False,  # university-wide graduation credits unsupported
    'gen_ed_degree_wide': False,
    'residency': False,
    'double_counting': False,
    'substitutions_transfer_ap_ib': False,
    'admission_progression': False,
    'course_offerings': False,
    'other_catalog_notes': False,
}

def evaluate_program(program, checklist, *, course_rules=None, required_courses=()):
    """Return eligibility plus actionable blockers. Never infer approval."""
    review = assess(program, checklist) if checklist is not None else {
        'internally_reviewed_for_planning': False,
        'blockers': ['no_whole_program_checklist'],
    }
    blockers = list(review['blockers'])
    if not review['internally_reviewed_for_planning']:
        blockers.append('whole_program_review_incomplete')
    if not required_courses:
        blockers.append('no_verified_full_requirement_expansion')
    if course_rules is None:
        blockers.append('course_rule_database_missing')
    else:
        for code in sorted(set(required_courses)):
            rule = course_rules.get(code)
            if rule is None or getattr(rule, 'status', None) != 'reviewed_course_description':
                blockers.append('missing_reviewed_course:' + code)
    if checklist is not None:
        for category in CATEGORIES:
            entry = checklist.get('categories', {}).get(category, {})
            if entry.get('status') == 'verified' and not CAPABILITIES[category]:
                blockers.append('unsupported_planner_constraint:' + category)
    return {'program_id': program.get('id'), 'eligible': not blockers,
            'blockers': sorted(set(blockers)), 'degree_certified': False,
            'notice': 'Internal planning eligibility only; never an official UNC degree audit.'}


def evaluate_combination(selections, registry, reviews, checklists, *, course_rules=None,
                         expanded_courses=None, compatibility_attestation=None):
    """Validate selection, then require every program and cross-program rules.

    compatibility_attestation is a separately verified human record; a bare
    boolean is never sufficient to attest to overlap and degree-wide rules.
    """
    from .catalog_registry import validate_selection
    validate_selection(selections, registry)
    programs = {p['id']: p for p in reviews.get('programs', [])}
    check_by_id = {c['program_id']: c for c in checklists}
    expanded_courses = expanded_courses or {}
    results = []
    blockers = []
    for item in selections:
        pid = item['id']
        if pid not in programs:
            blockers.append('missing_program_review:' + pid)
            continue
        result = evaluate_program(programs[pid], check_by_id.get(pid),
                                  course_rules=course_rules,
                                  required_courses=expanded_courses.get(pid, ()))
        results.append(result)
        blockers.extend(pid + ':' + b for b in result['blockers'])
    if len(selections) > 1:
        att = compatibility_attestation or {}
        selected_ids = sorted(p['id'] for p in selections)
        if (att.get('program_ids') != selected_ids or
            att.get('catalog_year') != '2026-2027' or
            att.get('double_counting_reviewed') is not True or
            att.get('degree_wide_requirements_reviewed') is not True or
            not att.get('human_reviewer') or
            not att.get('evidence_urls')):
            blockers.append('combination_compatibility_not_human_verified')
    return {'eligible': not blockers, 'blockers': sorted(set(blockers)),
            'programs': results, 'degree_certified': False,
            'notice': 'No graduation certification. Unsupported rules block real degree planning.'}
