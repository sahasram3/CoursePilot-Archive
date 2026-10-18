"""Single canonical provisional policy entry point.

Legacy degree_policy remains as a deprecated compatibility module for historic
unit tests and trusted-store parsing, but is never used to audit new roadmaps.
"""
from .policy_v22 import audit as audit_official
from .unc_official_policy_2026 import CourseRecord
from .cohort_gen_ed import audit_gen_ed


def audit_roadmap_policy(*, completed, planned, verified_credits, entering_term=None,
                         origins=None, programs=None, degree_type=None,
                         verified_mapping=False, unc_gpa=None,
                         program_gpas=None, program_minimum_credits=None):
    completed=list(completed);planned=list(planned)
    origins=origins or {}
    blockers=[]
    if len(completed)!=len(set(completed)) or len(planned)!=len(set(planned)):
        blockers.append('duplicate_course_entry')
    if set(completed)&set(planned):blockers.append('course_both_completed_and_planned')
    if not isinstance(verified_credits,dict):
        raise TypeError('verified_credits must be a server-owned dictionary')
    records=[]
    for code in sorted(set(completed)|set(planned)):
        credit=verified_credits.get(code)
        if type(credit) is not int or credit<=0:
            blockers.append('missing_verified_credit:'+str(code));continue
        origin=origins.get(code,'unknown')
        if origin not in ('unc','transfer','exam','unknown'):
            blockers.append('invalid_course_origin:'+str(code));origin='unknown'
        records.append(CourseRecord(code,credit,origin,
                                    'completed' if code in completed else 'planned'))
    # Never trust a caller's claims that a review has occurred. The official
    # provisional audit always returns degree_certified=False.
    policy=audit_official(records,programs=programs,degree_type=degree_type,
                          cohort=entering_term,unc_gpa=unc_gpa,
                          program_gpas=program_gpas,
                          verified_mapping=verified_mapping,
                          gen_ed_verified=False,
                          program_minimum_credits=program_minimum_credits)
    gen_ed=audit_gen_ed(entering_term=entering_term)
    return {**policy,'eligible':False,'degree_certified':False,
            'blockers':sorted(set(policy['blockers']+gen_ed['blockers']+blockers)),
            'gen_ed_audit':gen_ed,'policy_engine':'authoritative_v23',
            'notice':'Provisional audit; no academic certification.'}
