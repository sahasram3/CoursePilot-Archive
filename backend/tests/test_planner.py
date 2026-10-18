"""End-to-end planning for the Mathematics B.A. on real 2026-2027 catalog data."""
import random
import time

import pytest

from prereqpath.planner import plan
from prereqpath.planner.engine import PlanningError, prepare
from prereqpath.planner.schemas import PlanRequest
from prereqpath.planner.validate import validate_schedule
from prereqpath.store import get_store

MATH = "mathematics-major-ba"


def make(**kw):
    base = dict(programs=[MATH], entry_term="Fall 2026", first_term="Spring 2027", graduation_term="Spring 2030")
    base.update(kw)
    return PlanRequest(**base)


def schedule_of(plan_):
    return {c.code: i for i, t in enumerate(plan_.terms) for c in t.courses}


def term_of(plan_, code):
    return schedule_of(plan_).get(code)


def statuses(nodes):
    out = {}
    for n in nodes:
        out[n.id] = n.status
        out.update(statuses(n.children))
    return out


def check_consistent(request, response):
    """Independent re-validation + requirement completeness for every returned plan."""
    ctx = prepare(request)
    for p in response.plans:
        assert validate_schedule(ctx, schedule_of(p)) == []
        st = statuses(p.requirements[MATH])
        assert st["core"] in ("planned", "completed") and st["additional"] in ("planned", "completed")
        assert p.summary["projected_total_hours"] >= 120
        for t in p.terms:
            if not t.term.startswith("Summer"):
                assert request.min_credits <= t.total_credits <= request.max_credits
    assert response.graduation_certified is False
    assert response.plan_status == "provisional"


def test_first_year_with_calculus_in_progress():
    req = make(completed=[{"code": "MATH 231", "in_progress": True}])
    r = plan(req)
    assert r.status == "feasible"
    check_consistent(req, r)
    p = r.plans[0]
    # prerequisite chain order
    assert term_of(p, "MATH 232") < term_of(p, "MATH 233") if term_of(p, "MATH 233") is not None else True
    calc3 = term_of(p, "MATH 233") if term_of(p, "MATH 233") is not None else term_of(p, "MATH 235")
    assert term_of(p, "MATH 232") < calc3 < term_of(p, "MATH 383")
    assert term_of(p, "MATH 381") < term_of(p, "MATH 521")
    assert "MATH 231" not in schedule_of(p)              # already in progress
    assert "MATH 110" not in schedule_of(p)              # no needless remediation
    st = statuses(p.requirements[MATH])
    assert st["additional.calc1"] == "completed"
    # the 233/235 choice uses exactly one option; the other is marked not needed
    assert sorted([st["additional.calc3.233"], st["additional.calc3.235"]]) == ["not_needed", "planned"]
    elective_node = next(n for n in p.requirements[MATH][0].children if n.id == "core.upper_electives")
    assert len(elective_node.courses) == 3
    assert all(int(c["code"].split()[1][:3]) > 500 for c in elective_node.courses)
    assert "MATH 521" not in [c["code"] for c in elective_node.courses]   # no double counting


def test_no_placement_pulls_in_prerequisite_chain_with_grade_contingencies():
    req = make(first_term="Fall 2026")
    r = plan(req)
    assert r.status == "feasible"
    check_consistent(req, r)
    p = r.plans[0]
    order = [term_of(p, c) for c in ("MATH 110", "MATH 130", "MATH 231", "MATH 232")]
    assert order == sorted(order) and len(set(order)) == 4
    calc2 = next(c for t in p.terms for c in t.courses if c.code == "MATH 232")
    assert any("C- or better in MATH 231" in x for x in calc2.contingencies)


def test_placement_token_skips_precalculus():
    req = make(first_term="Fall 2026", tokens=["PLACEMENT:MATH 231"])
    r = plan(req)
    check_consistent(req, r)
    sched = schedule_of(r.plans[0])
    assert "MATH 110" not in sched and "MATH 130" not in sched
    assert sched["MATH 231"] == 0
    calc1 = next(c for c in r.plans[0].terms[0].courses if c.code == "MATH 231")
    assert any("PLACEMENT:MATH 231" in w for w in calc1.warnings)


def test_exam_credit_counts_and_is_reported():
    req = make(completed=[{"code": "MATH 231", "origin": "exam"}, {"code": "MATH 232", "origin": "exam"}])
    r = plan(req)
    check_consistent(req, r)
    sched = schedule_of(r.plans[0])
    assert "MATH 231" not in sched and "MATH 232" not in sched
    assert r.plans[0].summary["completed_hours"] == 8


def test_low_grade_forces_retake_before_dependent_course():
    req = make(completed=[{"code": "MATH 231", "grade": "D"}])
    r = plan(req)
    assert r.status == "feasible"
    check_consistent(req, r)
    p = r.plans[0]
    assert term_of(p, "MATH 231") < term_of(p, "MATH 232")
    retake = next(c for t in p.terms for c in t.courses if c.code == "MATH 231")
    assert any("Retake" in x for x in retake.reasons)
    assert p.summary["projected_total_hours"] >= 120


def test_good_grades_mean_no_assumption_warnings():
    req = make(completed=[{"code": "MATH 231", "grade": "A-"}])
    r = plan(req)
    for t in r.plans[0].terms:
        for c in t.courses:
            assert not any("Assumes your" in w for w in c.warnings)


def test_missing_grade_is_flagged_only_where_it_matters():
    req = make(completed=[{"code": "MATH 231"}])
    r = plan(req)
    calc2 = next(c for t in r.plans[0].terms for c in t.courses if c.code == "MATH 232")
    assert any("Assumes your MATH 231 grade is C- or better" in w for w in calc2.warnings)


def test_cross_listed_and_honors_completions_count():
    req = make(completed=[{"code": "MATH 231H", "grade": "A"}, {"code": "MATH 232", "grade": "A"},
                          {"code": "STOR 235", "grade": "B"}])
    r = plan(req)
    check_consistent(req, r)
    st = statuses(r.plans[0].requirements[MATH])
    assert st["additional.calc1"] == "completed"       # honors section of MATH 231
    assert st["additional.calc3"] == "completed"       # STOR 235 is cross-listed with MATH 235
    assert "MATH 233" not in schedule_of(r.plans[0]) and "MATH 235" not in schedule_of(r.plans[0])


def test_excluding_a_course_uses_the_alternative():
    req = make(completed=[{"code": "MATH 231", "grade": "A"}], exclude=["MATH 347"])
    r = plan(req)
    check_consistent(req, r)
    sched = schedule_of(r.plans[0])
    assert "MATH 347" not in sched and "MATH 577" in sched
    assert sched["MATH 577"] > sched["MATH 383"]       # MATH 577 needs MATH 381 and 383


def test_lab_bundle_counts_as_one_elective_when_completed():
    done = [{"code": c, "grade": "A"} for c in ("MATH 231", "MATH 232", "MATH 233", "MATH 383", "MATH 383L",
                                                 "MATH 528", "MATH 528L", "MATH 529", "MATH 529L")]
    r = plan(make(completed=done))
    electives = next(n for n in r.plans[0].requirements[MATH][0].children if n.id == "core.upper_electives")
    used = sorted(c["code"] for c in electives.courses)
    assert {"MATH 383L", "MATH 528L", "MATH 529L"} <= set(used)
    assert electives.status == "completed"           # 528 + 529 + the three-lab bundle


def test_locks_are_honored():
    req = make(completed=[{"code": "MATH 231", "grade": "A"}], locks=[{"code": "MATH 381", "term": "Fall 2027"}])
    r = plan(req)
    check_consistent(req, r)
    assert r.plans[0].terms[1].term == "Fall 2027"
    assert term_of(r.plans[0], "MATH 381") == 1


def test_impossible_lock_is_explained():
    req = make(completed=[{"code": "MATH 231", "grade": "A"}], locks=[{"code": "MATH 521", "term": "Spring 2027"}])
    r = plan(req)
    assert r.status == "infeasible"
    assert any("MATH 521 in Spring 2027" in c for c in r.infeasibility.causes)
    assert any("Removing your course locks" in s for s in r.infeasibility.suggestions)


def test_short_horizon_is_explained_with_chain_and_fix():
    r = plan(make(first_term="Fall 2026", graduation_term="Spring 2028"))
    assert r.status == "infeasible" and not r.plans
    text = " ".join(r.infeasibility.causes)
    assert "MATH 110 -> MATH 130 -> MATH 231 -> MATH 232" in text
    assert "UNC requires 120" in text
    assert any("Graduating in" in s for s in r.infeasibility.suggestions)


def test_placement_suggested_when_it_is_the_fix():
    # 45 transfer hours (not in the UNC catalog, so counted as hours only), no calculus,
    # five semesters left: MATH 110 -> ... -> MATH 383 needs six, so only placement fixes it.
    transfer = [{"code": f"XFER {100 + i}", "credits": 9, "origin": "transfer"} for i in range(5)]
    req = make(first_term="Fall 2026", graduation_term="Fall 2028", completed=transfer)
    r = plan(req)
    assert r.status == "infeasible"
    assert any("placement into MATH 231" in s for s in r.infeasibility.suggestions)
    fixed = make(first_term="Fall 2026", graduation_term="Fall 2028", completed=transfer, tokens=["PLACEMENT:MATH 231"])
    r2 = plan(fixed)
    assert r2.status == "feasible"
    check_consistent(fixed, r2)
    assert r2.plans[0].summary["transfer_hours"] == 45


def test_ba_subject_cap_applies_to_total_hours():
    done = [{"code": c, "grade": "A"} for c in ("MATH 110", "MATH 130", "MATH 231", "MATH 232", "MATH 233", "MATH 235",
                                                 "MATH 347", "MATH 381", "MATH 383", "MATH 521", "MATH 522", "MATH 523",
                                                 "MATH 524", "MATH 528", "MATH 533", "MATH 534")]
    req = make(first_term="Spring 2028", completed=done)
    r = plan(req)
    s = r.plans[0].summary
    assert s["ba_subject_cap_applies"] and "MATH" in s["subjects_over_45_hours"]
    assert s["countable_hours_after_ba_cap"] >= 120
    assert s["projected_total_hours"] > s["countable_hours_after_ba_cap"]   # excess MATH hours don't count


def test_alternatives_are_distinct():
    req = make(completed=[{"code": "MATH 231", "grade": "A"}], alternatives=3)
    r = plan(req)
    check_consistent(req, r)
    assert len(r.plans) == 3
    assert len({tuple(sorted(schedule_of(p).items())) for p in r.plans}) == 3


def test_policy_warnings():
    r = plan(make(entry_term="Fall 2024", first_term="Spring 2027", graduation_term="Spring 2030",
                  completed=[{"code": "MATH 231", "grade": "A"}]))
    codes = {i.code for i in r.issues}
    assert "catalog_year_mismatch" in codes       # 2024 entrants are governed by an archived catalog
    assert "ninth_semester" in codes             # Fall 2024 -> Spring 2030 is 12 regular semesters
    assert "offerings_unverified" in codes


@pytest.mark.parametrize("bad", [
    dict(programs=["no-such-program"]),
    dict(programs=["biology-major-bs"]),                     # discovered but not yet reviewed
    dict(graduation_term="Fall 2026"),
    dict(first_term="Spring 2026"),
    dict(graduation_term="Summer 2029"),
    dict(locks=[{"code": "MATH 381", "term": "Fall 2040"}]),
    dict(programs=[MATH, MATH]),
])
def test_invalid_requests_rejected(bad):
    with pytest.raises(PlanningError):
        plan(make(**bad))


def test_unreviewed_program_message_is_specific():
    with pytest.raises(PlanningError, match="does not have reviewed requirements"):
        plan(make(programs=["biology-major-bs"]))


def test_performance():
    start = time.perf_counter()
    plan(make(first_term="Fall 2026", graduation_term="Spring 2030"))
    assert time.perf_counter() - start < 10


def test_random_transcripts_always_yield_valid_plans_or_explanations():
    rng = random.Random(2026)
    pool = ["MATH 231", "MATH 232", "MATH 233", "MATH 235", "MATH 381", "MATH 347", "MATH 383", "MATH 521",
            "MATH 548", "MATH 550", "STOR 215", "COMP 110"]
    grades = [None, "A", "B", "C", "C-", "D"]
    for _ in range(12):
        done = [{"code": c, "grade": rng.choice(grades)} for c in rng.sample(pool, rng.randint(0, 6))]
        req = make(completed=done, tokens=rng.choice([[], ["PLACEMENT:MATH 231"]]),
                   graduation_term=rng.choice(["Spring 2029", "Spring 2030"]), first_term="Fall 2026")
        r = plan(req)
        if r.status == "feasible":
            check_consistent(req, r)
        else:
            assert r.infeasibility.causes and r.infeasibility.suggestions
