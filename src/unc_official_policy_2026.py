"""Source-backed UNC 2026-27 university policy facts and conservative checks.

Official catalog transcription; NOT independently audited by UNC or a second reviewer.
This module intentionally does not mark a policy as 'reviewed' in trusted_policy_store.
"""
from dataclasses import dataclass
from typing import Optional

DEGREE_URL='https://catalog.unc.edu/undergraduate/degree-requirements/'
IDEAS_URL='https://catalog.unc.edu/undergraduate/ideas-in-action/'
CATALOG_YEAR='2026-2027'

FACTS={
 'min_graduation_credits': {'value':120,'source':DEGREE_URL,'section':'Requirements for Undergraduate Degree Programs','qualification':'Some B.S. programs require more'},
 'min_unc_credits': {'value':45,'source':DEGREE_URL,'section':'Requirements for Undergraduate Degree Programs','qualification':'Qualifying UNC credit; transfer-credit study abroad excluded'},
 'min_unc_gpa': {'value':2.0,'source':DEGREE_URL,'section':'Requirements for Undergraduate Degree Programs','qualification':'Final cumulative GPA on UNC attempted coursework'},
 'min_major_core_unc_fraction': {'value':0.5,'source':DEGREE_URL,'section':'Requirements for Majors','qualification':'At least half of major core courses AND core credit hours at UNC'},
 'min_minor_core_unc_credits': {'value':9,'source':DEGREE_URL,'section':'Requirements for Minors','qualification':'Some minors require more'},
 'min_exclusive_core_fraction': {'value':0.5,'source':DEGREE_URL,'section':'Combining Majors and Minors','qualification':'STRICTLY greater than half of both courses and credits must be exclusive for EACH program'},
 'max_ba_subject_credits': {'value':45,'source':DEGREE_URL,'section':'Requirements for Undergraduate Degree Programs','qualification':'College of Arts and Sciences B.A.; excludes ENGL 100, 105, 105I'},
 'min_minor_core_unc_gpa': {'value':2.0,'source':DEGREE_URL,'section':'Requirements for Minors','qualification':'UNC minor-core GPA, program may require higher'},
 'min_major_core_unc_gpa': {'value':2.0,'source':DEGREE_URL,'section':'Requirements for Majors','qualification':'UNC major-core GPA, program may require higher'},
}

@dataclass(frozen=True)
class CourseRecord:
    code: str
    credits: int
    origin: str  # unc, transfer, exam, unknown
    status: str = 'completed'  # completed, planned
    subject: Optional[str] = None

    def __post_init__(self):
        if not self.code or type(self.credits) is not int or self.credits<=0:
            raise ValueError('Valid course code and positive integer verified credits required')
        if self.origin not in ('unc','transfer','exam','unknown') or self.status not in ('completed','planned'):
            raise ValueError('Invalid origin or completion status')


def audit_official_facts(courses, *, degree_type=None, programs=None, unc_gpa=None,
                         catalog_year=CATALOG_YEAR, include_gen_ed=True):
    """Provisional source-backed partial audit. Unknowns are blockers, never passes.

    programs: mapping program -> {'kind':'major'|'minor','core_courses':[codes]}
    The mapping is supplied for illustration; not trusted as an approved program map.
    """
    blockers=[]; notes=[]
    if catalog_year != CATALOG_YEAR: blockers.append('catalog_year_not_supported')
    by_code={}
    for course in courses:
        if course.code in by_code:
            if by_code[course.code] != course:
                blockers.append('conflicting_duplicate_course:'+course.code)
            else:
                blockers.append('duplicate_course_record:'+course.code)
        by_code[course.code]=course
    if not by_code: blockers.append('missing_transcript_and_plan')
    if any(c.origin=='unknown' for c in by_code.values()): blockers.append('unknown_course_origin')
    completed=[c for c in by_code.values() if c.status=='completed']
    all_credits=sum(c.credits for c in by_code.values())
    earned=sum(c.credits for c in completed)
    unc_earned=sum(c.credits for c in completed if c.origin=='unc')
    unc_projected=sum(c.credits for c in by_code.values() if c.origin=='unc')
    if all_credits<120: blockers.append('minimum_120_credits_not_met_in_plan')
    if unc_projected<45: blockers.append('minimum_45_unc_credits_not_met_in_plan')
    if unc_earned<45: notes.append('minimum_45_unc_credits_not_yet_earned')
    if unc_gpa is None: blockers.append('unc_cumulative_gpa_unknown')
    elif not isinstance(unc_gpa,(int,float)) or isinstance(unc_gpa,bool) or not 0<=unc_gpa<=4:
        blockers.append('invalid_unc_cumulative_gpa')
    elif unc_gpa<2: blockers.append('unc_cumulative_gpa_below_2')
    if degree_type not in ('BA','BS','other'):
        blockers.append('degree_type_not_verified')
    elif degree_type=='BS': blockers.append('bs_program_specific_credit_minimum_not_verified')
    elif degree_type=='BA':
        by_subject={}
        for c in by_code.values():
            subject=c.subject or c.code.split()[0]
            if c.code in ('ENGL 100','ENGL 105','ENGL 105I'): continue
            by_subject[subject]=by_subject.get(subject,0)+c.credits
        if any(n>45 for n in by_subject.values()): blockers.append('ba_subject_credit_cap_exceeded')
    # The live 2026-27 HTML page does not establish a 24-of-last-30 rule.
    # Do not import that rule from an older PDF without reconciling versions.
    if include_gen_ed: blockers.append('cohort_specific_ideas_requirements_not_verified')
    if programs is None: blockers.append('program_core_mappings_not_verified')
    else:
        uses={}
        for pid, spec in programs.items():
            kind=spec.get('kind')
            core=spec.get('core_courses',[])
            if kind not in ('major','minor') or not core or len(core)!=len(set(core)):
                blockers.append('invalid_program_core:'+pid); continue
            missing=set(core)-set(by_code)
            if missing: blockers.append('missing_core_courses:'+pid)
            for code in core: uses.setdefault(code,set()).add(pid)
            if not missing:
                exclusive=[by_code[code] for code in core if len([p for p,s in programs.items() if code in s.get('core_courses',[])])==1]
                exclusive_hours=sum(c.credits for c in exclusive)
                total_hours=sum(by_code[code].credits for code in core)
                if 2*len(exclusive)<=len(core) or 2*exclusive_hours<=total_hours:
                    blockers.append('exclusive_core_majority_not_met:'+pid)
                unc_core=[by_code[code] for code in core if by_code[code].origin=='unc']
                if kind=='major' and (2*len(unc_core)<len(core) or 2*sum(c.credits for c in unc_core)<total_hours):
                    blockers.append('major_half_core_at_unc_not_met:'+pid)
                if kind=='minor' and sum(c.credits for c in unc_core)<9:
                    blockers.append('minor_nine_unc_core_hours_not_met:'+pid)
            blockers.append('program_specific_rules_and_core_gpa_not_verified:'+pid)
    return {'degree_certified':False,'eligible':False,'blockers':sorted(set(blockers)),
            'notes':notes,'earned_credits':earned,'planned_plus_earned_credits':all_credits,
            'unc_earned_credits':unc_earned,'unc_projected_credits':unc_projected,
            'source_urls':[DEGREE_URL,IDEAS_URL], 'catalog_year':CATALOG_YEAR}
