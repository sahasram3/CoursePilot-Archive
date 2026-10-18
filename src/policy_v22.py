"""Fail-closed, source-backed provisional degree policy evaluation.

Not an academic certification or independent review. All mappings must be supplied
by trusted backend code for any future production use.
"""
from collections import Counter
from math import isfinite
from .unc_official_policy_2026 import CourseRecord, CATALOG_YEAR, DEGREE_URL


def audit(courses, *, programs=None, degree_type=None, cohort=None,
          unc_gpa=None, program_gpas=None, verified_mapping=False,
          gen_ed_verified=False, program_minimum_credits=None):
    blockers=[]; notes=[]
    records={}
    for course in courses:
        if not isinstance(course, CourseRecord):
            raise TypeError('Only validated CourseRecord objects are accepted')
        if course.code in records:
            blockers.append('duplicate_course:'+course.code)
        else:
            records[course.code]=course
    if not records: blockers.append('no_course_records')
    if any(c.origin=='unknown' for c in records.values()):blockers.append('unknown_course_origin')
    if any(c.status=='planned' and c.origin!='unknown' for c in records.values()):
        # Future location of study is not an earned-credit fact; a verified enrollment
        # intent may be projected, but never silently inferred from the course code.
        notes.append('future_course_origin_is_provisional')
    total=sum(c.credits for c in records.values())
    earned=sum(c.credits for c in records.values() if c.status=='completed')
    unc_earned=sum(c.credits for c in records.values() if c.status=='completed' and c.origin=='unc')
    if program_minimum_credits is not None and (type(program_minimum_credits)!=int or program_minimum_credits<120):
        blockers.append('invalid_program_credit_minimum')
    threshold=max(120,program_minimum_credits) if type(program_minimum_credits)==int and program_minimum_credits>=120 else 120
    if total<threshold:blockers.append('insufficient_total_credits')
    if unc_earned<45:notes.append('45_unc_credits_not_yet_earned')
    projected_unc=unc_earned+sum(c.credits for c in records.values() if c.status=='planned' and c.origin=='unc')
    if projected_unc<45:blockers.append('insufficient_projected_unc_credits')
    if degree_type not in ('BA','BS'):blockers.append('degree_type_unknown')
    if degree_type=='BS' and program_minimum_credits is None:blockers.append('bs_specific_minimum_unverified')
    if degree_type=='BA':
        subject_credits=Counter()
        for c in records.values():
            if c.code in ('ENGL 100','ENGL 105','ENGL 105I'):continue
            subject_credits[c.subject or c.code.split()[0]]+=c.credits
        if any(v>45 for v in subject_credits.values()):blockers.append('ba_subject_limit_requires_exception_review')
    if unc_gpa is None: blockers.append('unc_gpa_unknown')
    elif type(unc_gpa) not in (int,float) or not isfinite(unc_gpa) or not 0<=unc_gpa<=4:
        blockers.append('unc_gpa_invalid')
    elif unc_gpa<2: blockers.append('unc_gpa_below_minimum')
    if not cohort or not isinstance(cohort,str):blockers.append('entering_cohort_unknown')
    if not gen_ed_verified:blockers.append('cohort_gen_ed_unverified')
    if not verified_mapping: blockers.append('program_mapping_unverified')
    if not programs: blockers.append('program_core_requirements_missing')
    else:
        use=Counter()
        for pid,spec in programs.items():
            core=spec.get('core_courses',[])
            if spec.get('kind') not in ('major','minor') or not core or len(core)!=len(set(core)):
                blockers.append('invalid_program_core:'+pid);continue
            use.update(core)
        for pid,spec in programs.items():
            core=spec.get('core_courses',[])
            if spec.get('kind') not in ('major','minor') or not core or len(core)!=len(set(core)):continue
            missing=set(core)-records.keys()
            if missing:blockers.append('missing_core:'+pid);continue
            hours=sum(records[c].credits for c in core)
            exclusive=[c for c in core if use[c]==1]
            exclusive_hours=sum(records[c].credits for c in exclusive)
            if len(exclusive)*2<=len(core) or exclusive_hours*2<=hours:
                blockers.append('core_exclusivity_failed:'+pid)
            unc_done=[c for c in core if records[c].status=='completed' and records[c].origin=='unc']
            unc_future=[c for c in core if records[c].status=='planned' and records[c].origin=='unc']
            unc_possible=unc_done+unc_future
            if spec['kind']=='major':
                if len(unc_possible)*2<len(core) or sum(records[c].credits for c in unc_possible)*2<hours:
                    blockers.append('major_unc_core_residency_insufficient:'+pid)
            elif sum(records[c].credits for c in unc_possible)<9:
                blockers.append('minor_unc_core_residency_insufficient:'+pid)
            if len(unc_future)>0:notes.append('future_core_residency_conditional:'+pid)
            gpa=(program_gpas or {}).get(pid)
            if gpa is None:blockers.append('program_core_gpa_unknown:'+pid)
            elif type(gpa) not in (int,float) or not isfinite(gpa) or not 0<=gpa<=4:
                blockers.append('program_core_gpa_invalid:'+pid)
            elif gpa<2:blockers.append('program_core_gpa_below_minimum:'+pid)
            blockers.append('program_specific_restrictions_unverified:'+pid)
    blockers.append('independent_policy_review_pending')
    return {'eligible':False,'degree_certified':False,'status':'provisional_only',
            'blockers':sorted(set(blockers)),'notes':sorted(set(notes)),
            'earned_credits':earned,'total_projected_credits':total,
            'unc_earned_credits':unc_earned,'unc_projected_credits':projected_unc,
            'source_url':DEGREE_URL,'catalog_year':CATALOG_YEAR}
