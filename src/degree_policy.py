"""Conservative cross-program credit and requirement audit.

This module evaluates explicitly supplied, source-reviewed policy; it does not
encode UNC graduation thresholds, Gen Ed rules, or double-count limits by guess.
"""
from dataclasses import dataclass
from collections import Counter

class PolicyError(ValueError): pass

@dataclass(frozen=True)
class Policy:
    catalog_year: str
    source_url: str
    reviewer: str
    min_total_credits: int
    gen_ed_groups: tuple[tuple[str, tuple[str,...], int], ...] = ()
    # each group: (name, eligible course codes, minimum distinct courses)
    max_shared_program_courses: int | None = None
    min_resident_credits: int | None = None
    status: str = 'draft'

    def __post_init__(self):
        if self.status not in ('draft','reviewed'): raise PolicyError('Invalid policy status')
        if not isinstance(self.min_total_credits,int) or not 1<=self.min_total_credits<=300:
            raise PolicyError('Invalid credit threshold')
        if self.max_shared_program_courses is not None and (not isinstance(self.max_shared_program_courses,int) or self.max_shared_program_courses<0):
            raise PolicyError('Invalid overlap limit')
        if self.min_resident_credits is not None and (not isinstance(self.min_resident_credits,int) or self.min_resident_credits<0):
            raise PolicyError('Invalid residency threshold')
        if self.status=='reviewed' and (not self.source_url.startswith('https://catalog.unc.edu/') or not self.reviewer.strip()):
            raise PolicyError('Reviewed policy requires UNC source and named reviewer')
        for name, options, count in self.gen_ed_groups:
            if not name or not options or len(set(options))!=len(options) or not isinstance(count,int) or count<1 or count>len(options):
                raise PolicyError('Invalid Gen Ed group')


def audit_degree(policy, *, completed=(), planned=(), credits=None, program_courses=None,
                 resident_courses=(), verified_course_credits=(), verified_program_mapping=False):
    """Fail closed on unknown facts; count unique courses once for total credits.

    'completed' and 'planned' are course codes; credits maps code -> verified
    positive integer credit hours. No invented credit hours or double credit.
    program_courses maps program id -> iterable of codes. Results are a
    provisional audit, never UNC certification.
    """
    if policy is None or policy.status!='reviewed':
        return {'eligible':False,'blockers':['unreviewed_degree_policy'],'degree_certified':False}
    completed=set(completed); planned=set(planned)
    all_courses=completed|planned
    credits=credits or {}
    blockers=[]
    if not all_courses: blockers.append('no_course_records')
    missing=sorted(c for c in all_courses if c not in credits or type(credits[c]) is not int or credits[c]<=0)
    if missing: blockers.extend('missing_verified_credits:'+c for c in missing)
    total=sum(credits[c] for c in all_courses if c not in missing)
    if not missing and total<policy.min_total_credits: blockers.append('insufficient_total_credits')
    for name, options, minimum in policy.gen_ed_groups:
        if len(all_courses.intersection(options))<minimum: blockers.append('gen_ed_unsatisfied:'+name)
    if policy.min_resident_credits is None: blockers.append('residency_rule_not_encoded')
    else:
        resident=set(resident_courses)
        if not resident<=completed: blockers.append('resident_course_not_completed_at_unc')
        if missing and resident.intersection(missing): blockers.append('resident_credits_unknown')
        elif sum(credits[c] for c in resident & completed if c in credits and type(credits[c]) is int and credits[c]>0)<policy.min_resident_credits:
            blockers.append('insufficient_resident_credits')
    if policy.max_shared_program_courses is None: blockers.append('double_count_rule_not_encoded')
    elif not verified_program_mapping: blockers.append('program_course_mapping_not_verified')
    else:
        programs=program_courses or {}
        if not programs: blockers.append('program_course_mapping_missing')
        else:
            counts=Counter(c for courses in programs.values() for c in set(courses))
            shared={c for c,n in counts.items() if n>1}
            if not set(counts)<=all_courses: blockers.append('program_course_missing_from_plan')
            if any(not isinstance(pid,str) or not pid.strip() for pid in programs): blockers.append('invalid_program_mapping')
            if len(shared)>policy.max_shared_program_courses: blockers.append('program_overlap_exceeds_reviewed_limit')
    return {'eligible':not blockers,'blockers':sorted(set(blockers)),
            'unique_credits':total,'unknown_credit_courses':missing,
            'degree_certified':False,'notice':'Provisional audit of supplied, source-reviewed rules only.'}
