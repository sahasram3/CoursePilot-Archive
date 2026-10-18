"""2026-27 UNC Mathematics BA program-core transcription; NOT a full degree audit.

Source: https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/
Reviewed against the live catalog heading '2026-2027 Academic Catalog' on 2026-10-17.
Course-level prerequisite descriptions and upper-level elective choices remain unverified.
"""
from dataclasses import dataclass
from typing import FrozenSet

SOURCE='https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/'
CATALOG='2026-2027'
FIXED_CREDITS={'MATH 231':4,'MATH 232':4,'MATH 381':3,'MATH 383':3,'MATH 521':3}
CHOICES={'calculus_3':('MATH 233','MATH 235'),'linear_algebra':('MATH 347','MATH 577')}
CHOICE_CREDITS={'MATH 233':4,'MATH 235':4,'MATH 347':3,'MATH 577':3}
UPPER_LEVEL_MATH_COUNT=3
UPPER_LEVEL_MATH_CREDITS=9
TOTAL_MAJOR_HOURS=33

@dataclass(frozen=True)
class CoreAudit:
    satisfied:tuple
    missing:tuple
    upper_level_completed:tuple
    notes:tuple
    major_complete:bool

def audit_math_ba(completed, *, statistics_major=False, upper_level_lab_bundle=False):
    """Conservative *program-core* check, not Gen Ed / GPA / residency / grades.

    completed: accepted course codes; caller must verify equivalencies and grades.
    Upper-level electives must be explicitly recognized as MATH 5xx+; this routine
    does not assume every 500+ course is eligible or that it has three credits.
    """
    done=set(completed)
    satisfied=[]; missing=[]
    for code in FIXED_CREDITS:
        if code=='MATH 381' and statistics_major and 'STOR 215' in done:
            satisfied.append('MATH 381 (STOR 215 substitution)')
        elif code in done:satisfied.append(code)
        else:missing.append(code)
    for key, options in CHOICES.items():
        selected=[c for c in options if c in done]
        if selected:satisfied.append(f'{key}: {selected[0]}')
        else:missing.append(f'{key}: one of {", ".join(options)}')
    # Electives cannot be mechanically certified from a course number alone:
    # special lab bundle and course exclusions require human review.
    upper=sorted(c for c in done if c.startswith('MATH ') and c.split()[-1].isdigit() and int(c.split()[-1])>500 and c!='MATH 521')
    notes=['Upper-level elective eligibility, exact hours, and the three-lab exception require verification.',
           'All university degree, Gen Ed, GPA, residency, and overlap rules are outside this audit.',
           'Official catalog says three additional MATH courses numbered above 500 (9 hours).']
    if upper_level_lab_bundle:notes.append('MATH 383L + 528L + 529L can count as one 500-level course, subject to review.')
    return CoreAudit(tuple(satisfied),tuple(missing),tuple(upper),tuple(notes),False)

def source_record():
    return {'program':'Mathematics Major, B.A.','catalog_year':CATALOG,'url':SOURCE,
            'core_requirement_table_reviewed':True,'degree_audit_verified':False,
            'hours':TOTAL_MAJOR_HOURS,'fixed_course_credits':FIXED_CREDITS,
            'choice_groups':CHOICES,'choice_credits':CHOICE_CREDITS,
            'upper_level':{'subject':'MATH','number_above':500,'count':3,'hours':9,
                           'exception':'MATH 383L + MATH 528L + MATH 529L counts as one course'},
            'special_substitution':'Current/former Statistics and Analytics majors may substitute STOR 215 for MATH 381',
            'unresolved':['Individual course prerequisite AND/OR rules','Elective eligibility and hours',
                          'Course term offerings','Grade and GPA checks','Double-counting',
                          'General Education','University graduation requirements']}
