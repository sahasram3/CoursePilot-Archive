"""Experimental requirement-choice and full-horizon planner.

Only runs on human-verified input; does not certify UNC graduation.
"""
from itertools import combinations, product
from .degree_rules import audit, validate_combination
from .planner import build, validate_plan

class PlanningError(ValueError):
    pass

def candidate_sets(programs, completed, courses, max_candidates=10000):
    validate_combination(programs)
    if not all(p.verified and p.catalog_year == '2026-2027' for p in programs):
        raise PlanningError('Every program must be reviewed for catalog 2026-2027')
    groups=[]
    for p in programs:
        for r in p.requirements:
            if not (r.verified and r.catalog_year == p.catalog_year and r.source_url):
                raise PlanningError('Unreviewed requirement: '+r.id)
            if r.kind not in ('ALL','ANY','AT_LEAST'):
                raise PlanningError('Unsupported requirement: '+r.id)
            count=len(r.courses) if r.kind=='ALL' else 1 if r.kind=='ANY' else r.count
            if not 1<=count<=len(r.courses):raise PlanningError('Invalid choice count: '+r.id)
            already=set(r.courses)&set(completed)
            outstanding=max(0,count-len(already))
            alternatives=list(combinations(sorted(set(r.courses)-set(completed)),outstanding))
            groups.append(alternatives)
    possibilities=1
    for group in groups:
        possibilities*=len(group)
        if possibilities>max_candidates:raise PlanningError('Too many combinations; narrow elective options')
    for selections in product(*groups):
        yield set().union(*map(set,selections)) if selections else set()

def generate(programs,courses,completed,calendar,min_credits=12,max_credits=18,locked=None,limit=3):
    """Generate distinct VALIDATED alternatives for a *complete supplied* course set.

    Assumes degree overlap is explicitly resolved by an advisor; DOES NOT validate
    program exclusivity, GPA, Gen Ed, course offering, residency, or enrollment.
    """
    if not 1<=limit<=20:raise PlanningError('Invalid alternative limit')
    seen=set();plans=[];reasons=[]
    for required in candidate_sets(programs,completed,courses):
        for seed in range(8):
            try:
                plan=build(courses,required,completed,calendar,min_credits,max_credits,seed,locked)
                validate_plan(courses,plan,completed,min_credits,max_credits)
                key=tuple((term,tuple(sorted(codes))) for term,codes in plan.items())
                if key not in seen:
                    seen.add(key)
                    plans.append({'terms':plan,'credits':{t:sum(courses[c].credits for c in codes) for t,codes in plan.items()},'required_courses':sorted(required),'status':'provisional_verified_subset','limitations':['Not a complete UNC degree audit','Degree overlap and Gen Ed not validated','Future course availability not confirmed']})
                    if len(plans)>=limit:return {'alternatives':plans,'errors':reasons[:5]}
            except (ValueError,KeyError) as exc:
                if str(exc) not in reasons:reasons.append(str(exc))
    return {'alternatives':plans,'errors':reasons[:5]}

def generate_with_prerequisite_graph(programs, rules, completed, calendar, *,
                                     grades=None, permissions=(), locked=None,
                                     min_credits=0, max_credits=18, limit=3):
    """Bridge verified degree choice groups to the source-gated prerequisite solver.

    Only reviewed, explicitly enumerated program requirements are accepted.
    This is NOT a full degree audit: wildcard elective groups and Gen Ed are
    intentionally unsupported until their rules are reviewed.
    """
    from .graph_optimizer import optimize_graph, PlanningRequest
    choices=candidate_sets(programs, completed, rules)
    plans=[]; errors=[]; seen=set()
    for required in choices:
        try:
            result=optimize_graph(rules,calendar,PlanningRequest(
                tuple(sorted(required)),tuple(completed),min_credits,max_credits,
                tuple(permissions),tuple(sorted((locked or {}).items()))),grades=grades,
                limit=max(1,limit-len(plans)))
            for plan in result['alternatives']:
                key=tuple((term,tuple(codes)) for term,codes in plan['terms'].items())
                if key not in seen:
                    seen.add(key);plans.append(plan)
                    if len(plans)>=limit:break
            if result['reason'] and result['reason'] not in errors:errors.append(result['reason'])
        except ValueError as exc:
            if str(exc) not in errors:errors.append(str(exc))
        if len(plans)>=limit:break
    return {'alternatives':plans,'errors':errors[:10],
            'status':'provisional_not_degree_certified'}
