"""Economics B.A. and the Mathematics + Economics double major on real catalog data."""
import os
import subprocess
import sys

from prereqpath.planner import plan
from prereqpath.planner.engine import prepare
from prereqpath.planner.schemas import PlanRequest
from prereqpath.planner.validate import validate_schedule
from prereqpath.store import get_store, walk

ECON, MATH = "economics-major-ba", "mathematics-major-ba"


def make(programs, **kw):
    base = dict(programs=programs, entry_term="Fall 2026", first_term="Spring 2027", graduation_term="Spring 2030")
    base.update(kw)
    return PlanRequest(**base)


def schedule_of(p):
    return {c.code: i for i, t in enumerate(p.terms) for c in t.courses}


def used(p, program_id):
    def collect(nodes):
        return {c["code"]: n.id for n in nodes for c in n.courses} | \
            {k: v for n in nodes for k, v in collect(n.children).items()}
    return collect(p.requirements[program_id])


def test_economics_is_verified_and_pinned_to_catalog_text():
    program = get_store("2026-2027").program(ECON)
    assert program.verification.status == "verified"
    grades = {n.course: n.min_grade for n in walk(program.requirements) if n.kind == "course"}
    assert grades["ECON 101"] == grades["ECON 400"] == grades["ECON 410"] == "C" and grades["ECON 420"] is None
    assert program.exclusive_groups == [["ECON 470", "ECON 570"]]


def test_economics_plan_structure_and_grade_contingencies():
    req = make([ECON], completed=[{"code": "MATH 231", "grade": "B"}])
    r = plan(req)
    assert r.status == "feasible"
    p = r.plans[0]
    assert validate_schedule(prepare(req), schedule_of(p)) == []
    s = schedule_of(p)
    assert s["ECON 101"] < s["ECON 410"] < s["ECON 420"] and s["ECON 101"] < s["ECON 400"]
    use = used(p, ECON)
    electives = [c for c, nid in use.items() if nid.startswith("core.electives")]
    assert len(electives) == 4
    assert any(int(c.split()[1][:3]) >= 500 for c in electives)                 # at least one 500+
    assert all(c not in ("ECON 493", "ECON 698", "ECON 400", "ECON 410", "ECON 420") for c in electives)
    econ101 = next(c for t in p.terms for c in t.courses if c.code == "ECON 101")
    assert any("C or better to count for Economics" in x for x in econ101.contingencies)
    assert p.summary["projected_total_hours"] >= 120 and r.graduation_certified is False


def test_mutually_exclusive_courses_are_never_both_planned(monkeypatch):
    # ECON 570 is not in the 2026-27 listings, so exercise the same constraint on two
    # courses that are: forcing both must be infeasible, forcing one must exclude the other.
    program = get_store("2026-2027").program(ECON)
    monkeypatch.setattr(program, "exclusive_groups", [["ECON 470", "ECON 510"]])
    done = [{"code": "MATH 231", "grade": "A"}, {"code": "ECON 101", "grade": "A"}]
    both = plan(make([ECON], completed=done, locks=[{"code": "ECON 470", "term": "Spring 2029"},
                                                    {"code": "ECON 510", "term": "Fall 2029"}]))
    assert both.status == "infeasible"
    one = plan(make([ECON], completed=done, locks=[{"code": "ECON 470", "term": "Spring 2029"}]))
    assert "ECON 510" not in schedule_of(one.plans[0])


def test_double_major_counts_shared_calculus_and_keeps_cores_exclusive():
    req = make([MATH, ECON], exams=[{"type": "AP", "exam": "Calculus BC", "score": 5}])
    r = plan(req)
    assert r.status == "feasible"
    p = r.plans[0]
    assert validate_schedule(prepare(req), schedule_of(p)) == []
    math_use, econ_use = used(p, MATH), used(p, ECON)
    assert math_use["MATH 231"] == "additional.calc1" and econ_use["MATH 231"] == "additional.calculus.231"
    for pid in (MATH, ECON):
        core = p.summary["major_core"][pid]
        assert core["half_at_unc_ok"]
    shared_core = set(p.summary["major_core"][MATH]["core_courses"]) & set(p.summary["major_core"][ECON]["core_courses"])
    assert len(shared_core) * 2 < len(p.summary["major_core"][MATH]["core_courses"])
    loads = [t.course_credits for t in p.terms]
    assert max(loads) <= 10, loads


def test_double_major_is_reproducible_across_processes():
    script = ("from prereqpath.planner import plan\nfrom prereqpath.planner.schemas import PlanRequest\n"
              "r = plan(PlanRequest(programs=['mathematics-major-ba','economics-major-ba'], entry_term='Fall 2026',"
              " first_term='Spring 2027', graduation_term='Spring 2030', exams=[{'type':'AP','exam':'Calculus BC','score':5}]))\n"
              "print('|'.join(','.join(c.code for c in t.courses) for t in r.plans[0].terms))")
    outputs = set()
    for seed in ("11", "22"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        outputs.add(subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env,
                                   check=True).stdout.strip())
    assert len(outputs) == 1


def test_same_major_twice_or_three_majors_rejected():
    import pytest
    from prereqpath.planner.engine import PlanningError
    with pytest.raises(PlanningError):
        plan(make([ECON, ECON]))
