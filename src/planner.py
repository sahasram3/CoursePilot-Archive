"""Verified-data-only full-horizon course sequencing prototype.
Does NOT solve degree electives, overlaps, Gen Ed, or live section availability.
"""
from dataclasses import dataclass
from typing import Tuple
from collections import defaultdict

@dataclass(frozen=True)
class Course:
    code:str
    credits:int
    prerequisites:Tuple[str,...]=()
    verified:bool=False
    # Every prerequisite here is an AND requirement. OR requirements need a richer schema.

@dataclass(frozen=True)
class Term:
    year:int
    season:str
    @property
    def label(self):return f'{self.season} {self.year}'

def terms(start_year,start_season,graduation_year,graduation_season,summer=False):
    order=['Spring','Summer','Fall']
    start=(start_year,order.index(start_season));end=(graduation_year,order.index(graduation_season))
    if start>end:raise ValueError('Graduation must not precede start')
    return [Term(y,s) for y in range(start_year,graduation_year+1) for s in order if (y,order.index(s))>=start and (y,order.index(s))<=end and (summer or s!='Summer')]

def validate_catalog(courses,required,completed):
    missing=set(required)-set(courses)-set(completed)
    if missing:raise ValueError('Missing course records: '+', '.join(sorted(missing)))
    for code in required:
        if code not in completed:
            c=courses[code]
            if not c.verified:raise ValueError('Unverified course: '+code)
            if not isinstance(c.credits,int) or c.credits<=0:raise ValueError('Invalid/variable credit hours require explicit resolution: '+code)
            for p in c.prerequisites:
                if p not in courses and p not in completed:raise ValueError('Unresolved prerequisite: '+p)

def build(courses,required,completed,calendar,min_credits=12,max_credits=18,seed=0,locked=None):
    """Returns a provisional sequence. Credit minimum includes only supplied courses;
    therefore if fewer than min_credits remain, report infeasible rather than pad.
    """
    if min_credits>max_credits or min_credits<0:raise ValueError('Invalid credit range')
    validate_catalog(courses,required,completed)
    locked=locked or {}
    remaining=set(required)-set(completed);done=set(completed);plan={}
    for t in calendar:
        choices=sorted([c for c in remaining if set(courses[c].prerequisites)<=done],key=lambda c:((sum(c in courses[x].prerequisites for x in remaining)*-1), (sum(ord(z) for z in c)+seed*37)%997))
        chosen=[];total=0
        for code in choices:
            forced=locked.get(code)
            if forced and forced!=t.label:continue
            cr=courses[code].credits
            if total+cr<=max_credits:
                chosen.append(code);total+=cr
        for code,term in locked.items():
            if term==t.label and code in remaining and code not in chosen:raise ValueError(f'Locked course {code} cannot be placed in {term}')
        # The minimum is not silently relaxed; last term may legitimately be underloaded,
        # but requires explicit user approval / electives, so flag it.
        if chosen and total<min_credits:raise ValueError(f'{t.label} has only {total} modeled credits; add verified electives or allow underload')
        plan[t.label]=chosen
        remaining-=set(chosen);done.update(chosen)
    if remaining:raise ValueError('Cannot fit required courses by graduation: '+', '.join(sorted(remaining)))
    return plan

def validate_plan(courses,plan,completed,min_credits=12,max_credits=18):
    done=set(completed);seen=set()
    for term,selected in plan.items():
        if len(selected)!=len(set(selected)):raise ValueError('Duplicate course in '+term)
        total=0
        for code in selected:
            if code in seen or code in done:raise ValueError('Repeated course '+code)
            c=courses[code]
            if not c.verified:raise ValueError('Unverified '+code)
            if not set(c.prerequisites)<=done:raise ValueError('Prerequisite violation '+code)
            total+=c.credits
        if selected and not(min_credits<=total<=max_credits):raise ValueError(f'Credit limit violation in {term}: {total}')
        seen.update(selected);done.update(selected)
    return True
