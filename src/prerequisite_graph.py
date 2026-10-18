"""Program-agnostic, conservative prerequisite graph with evidence-backed AND/OR rules.

Prerequisite clauses are ANDed; each clause contains OR alternatives. Course grades
are checked when known; unknown grades cannot satisfy a minimum-grade rule.
External permissions/placement are modeled as explicit tokens, not assumed.
"""
from dataclasses import dataclass
from typing import Tuple

GRADES={'A+':12,'A':11,'A-':10,'B+':9,'B':8,'B-':7,'C+':6,'C':5,'C-':4,'D+':3,'D':2,'D-':1,'F':0}

@dataclass(frozen=True)
class Alternative:
    course: str
    minimum_grade: str | None = None

@dataclass(frozen=True)
class CourseRule:
    code: str
    credits: int
    clauses: Tuple[Tuple[Alternative,...],...] = ()
    source_url: str = ''
    source_excerpt: str = ''
    status: str = 'reviewed_course_description'
    notes: str = ''

    def __post_init__(self):
        if not self.code or not (1 <= self.credits <= 18): raise ValueError('Invalid course or credits')
        if not self.source_url.startswith('https://catalog.unc.edu/') or not self.source_excerpt:
            raise ValueError('Source URL and excerpt required')
        for clause in self.clauses:
            if not clause: raise ValueError('Empty prerequisite OR clause')
            for alt in clause:
                if alt.minimum_grade is not None and alt.minimum_grade not in GRADES:
                    raise ValueError('Unknown minimum grade')

def eligible(rule, completed, *, grades=None, permissions=()):
    """Returns (bool, unsatisfied OR clauses). Completed may be a set of course codes.
    Tokens such as PLACEMENT:MATH232 must be explicitly present in permissions.
    """
    grades=grades or {}; done=set(completed); tokens=set(permissions)
    def ok(alt):
        if alt.course.startswith('PLACEMENT:') or alt.course.startswith('PERMISSION:'):
            return alt.course in tokens
        if alt.course not in done: return False
        if alt.minimum_grade is None: return True
        return grades.get(alt.course) in GRADES and GRADES[grades[alt.course]] >= GRADES[alt.minimum_grade]
    missing=tuple(tuple(a.course+(f' >= {a.minimum_grade}' if a.minimum_grade else '') for a in clause)
                  for clause in rule.clauses if not any(ok(a) for a in clause))
    return not missing, missing

def validate_sequence(semesters, rules, *, completed=(), grades=None, permissions=()):
    """Checks that prerequisites were completed BEFORE the course's term."""
    done=set(completed); issues=[]
    for i, term in enumerate(semesters):
        for code in term:
            if code not in rules:
                issues.append({'term':i,'course':code,'reason':'course not verified in graph'})
                continue
            good,missing=eligible(rules[code],done,grades=grades,permissions=permissions)
            if not good: issues.append({'term':i,'course':code,'missing':missing})
        done.update(term)
    return issues

def dependency_edges(rules):
    return sorted({(a.course,code) for code,rule in rules.items() for clause in rule.clauses for a in clause})

def explain(course, rules, completed=(), *, grades=None, permissions=()):
    if course not in rules: return {'course':course,'status':'unknown','warning':'Course not in reviewed graph'}
    ok,missing=eligible(rules[course],completed,grades=grades,permissions=permissions)
    unlocks=sorted(code for code,rule in rules.items() if code!=course and any(a.course==course for clause in rule.clauses for a in clause))
    return {'course':course,'eligible':ok,'missing':missing,'unlocks':unlocks,'source':rules[course].source_url}
