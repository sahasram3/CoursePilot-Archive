"""Provisional full-roadmap evaluation. Never a graduation certification.

The policy must be supplied from a trusted reviewed registry by the calling service,
not from the student's HTTP request. No UNC-wide policy is bundled as reviewed.
"""
from .graph_optimizer import optimize_graph, PlanningRequest, ScheduleError
from .authoritative_audit import audit_roadmap_policy
from .prerequisite_graph import validate_sequence


def audit_roadmap(rules, calendar, request, *, policy=None, credits=None,
                  program_courses=None, resident_completed=(),
                  verified_program_mapping=False, grades=None, limit=3,
                  entering_term=None, origins=None, degree_type=None):
    """Join sequencing with degree-wide audits; report blockers per alternative.

    A passing provisional policy audit is NOT sufficient for real degree eligibility:
    whole-program approval, catalog freshness and capability gate remain mandatory.
    """
    result=optimize_graph(rules,calendar,request,grades=grades,limit=limit)
    completed=set(request.completed)
    credit_map=credits if credits is not None else {c:r.credits for c,r in rules.items()}
    for plan in result['alternatives']:
        planned=[code for courses in plan['terms'].values() for code in courses]
        problems=validate_sequence(list(plan['terms'].values()),rules,
                                   completed=request.completed,grades=grades,
                                   permissions=request.permissions)
        if problems:
            raise ScheduleError('Internal sequence validation failed')
        # The old simplified overlap threshold is intentionally ignored.
        # No client- or test-provided Policy(status='reviewed') can certify UNC rules.
        audit=audit_roadmap_policy(
            completed=completed,planned=planned,verified_credits=credit_map,
            entering_term=entering_term,origins=origins,programs=None,
            degree_type=degree_type,verified_mapping=False)
        if policy is not None:
            audit['blockers']=sorted(set(audit['blockers']+['legacy_policy_not_authoritative']))
        plan['degree_audit']=audit
        plan['degree_ready']=False
        plan['audit_status']='provisional_only'
    result['degree_certified']=False
    result['status']='provisional_roadmap_audit'
    return result
