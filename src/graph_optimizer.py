"""Source-gated prerequisite-aware multi-term planner.

Generic for any UNC program; DOES NOT certify degree completion. Course records
must be individually reviewed. OR prerequisites and grade/permission exceptions
are evaluated with prerequisite_graph. No assumptions about term offerings.
"""
from dataclasses import dataclass
from .prerequisite_graph import eligible, validate_sequence

class ScheduleError(ValueError):
    pass

@dataclass(frozen=True)
class PlanningRequest:
    required: tuple[str, ...]
    completed: tuple[str, ...] = ()
    min_credits: int = 0
    max_credits: int = 18
    permissions: tuple[str, ...] = ()
    locked: tuple[tuple[str, str], ...] = ()


def optimize_graph(rules, calendar, request, *, grades=None, limit=3, max_states=250000):
    """Enumerate distinct feasible full-horizon sequences, with explicit coverage gaps.

    Zero min_credits means this models ONLY specified required courses, not
    general education/electives. Nonzero minima apply to every modeled term.
    Future term availability is UNKNOWN and never treated as confirmed.
    """
    if not 1 <= limit <= 20 or not 0 <= request.min_credits <= request.max_credits <= 30:
        raise ScheduleError('Invalid planning limits')
    labels=[t.label if hasattr(t,'label') else str(t) for t in calendar]
    if not labels or len(labels)!=len(set(labels)):raise ScheduleError('Calendar must contain unique terms')
    required=set(request.required)-set(request.completed)
    unknown=sorted(required-set(rules))
    if unknown:raise ScheduleError('Missing reviewed course rules: '+', '.join(unknown))
    for code in required:
        if rules[code].status != 'reviewed_course_description':
            raise ScheduleError('Unreviewed course rule: '+code)
    locked=dict(request.locked)
    if len(locked)!=len(request.locked):raise ScheduleError('Duplicate course locks')
    for code,term in locked.items():
        if code not in required or term not in labels:raise ScheduleError('Invalid lock: '+code+' / '+term)
    grades=grades or {}
    # A planned course's future grade is not known. If a later prerequisite
    # requires a minimum grade, the planner must not silently assume a pass.
    for code in required:
        for clause in rules[code].clauses:
            for alternative in clause:
                if alternative.minimum_grade and alternative.course in required:
                    raise ScheduleError('Future minimum-grade prerequisite cannot be guaranteed: '
                                        +alternative.course+' -> '+code)
    plans=[]; visited=0; truncated=False
    def walk(index,done,remaining,plan):
        nonlocal visited,truncated
        if len(plans)>=limit:return
        visited+=1
        if visited>max_states:
            truncated=True;return
        if index==len(labels):
            if remaining:return
            issues=validate_sequence([plan[t] for t in labels],rules,completed=request.completed,grades=grades,permissions=request.permissions)
            if issues:raise AssertionError('Internal prerequisite validation failed')
            plans.append({'terms':{t:list(plan[t]) for t in labels},
                          'credits':{t:sum(rules[c].credits for c in plan[t]) for t in labels},
                          'status':'provisional_course_sequence',
                          'warnings':['Does not verify full degree completion or Gen Ed',
                                      'Future course offerings and seats are unverified',
                                      'Prerequisite graph coverage is limited to supplied reviewed rules']})
            return
        term=labels[index]
        forced={c for c,t in locked.items() if t==term}
        if not forced<=remaining:return
        available=sorted(c for c in remaining if locked.get(c,term)==term and eligible(rules[c],done,grades=grades,permissions=request.permissions)[0])
        if not forced<=set(available):return
        # Enumerate subsets, largest first to favor earlier progress; empty term allowed
        # when minimum credits is zero (required courses may not fill a student's schedule).
        from itertools import combinations
        optional=[c for c in available if c not in forced]
        choices=[]
        for size in range(len(optional),-1,-1):
            for combo in combinations(optional,size):
                selection=tuple(sorted(forced|set(combo)))
                credits=sum(rules[c].credits for c in selection)
                if request.min_credits<=credits<=request.max_credits:
                    choices.append(selection)
        for selection in choices:
            plan[term]=selection
            walk(index+1,done|set(selection),remaining-set(selection),plan)
            if len(plans)>=limit or truncated:break
        plan.pop(term,None)
    walk(0,set(request.completed),required,{})
    return {'alternatives':plans,'search_truncated':truncated,'states_explored':visited,
            'status':'provisional_not_degree_certified',
            'reason':None if plans else ('Search limit reached' if truncated else 'No feasible course sequence under supplied rules and locks')}
