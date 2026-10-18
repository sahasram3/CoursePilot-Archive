"""CP-SAT semester planner.

Model
  x[c,t]   course c is scheduled in planning term t (at most once overall)
  u[n,c]   course c is used to satisfy requirement node n; within one program a
           course satisfies at most one requirement (no double counting)
  Prerequisites: x[c,t] => requisite tree of c holds using completed courses and
           courses scheduled strictly before t (or in t, for corequisites).
  Load:    min <= course hours + unassigned Gen Ed/elective hours <= max per term
  Degree:  completed + planned + unassigned hours >= 120, applying the B.A.
           45-hour per-subject cap to what counts.
Credit hours are handled in half-hour units because some courses carry 0.5/1.5.
Unresolved requirements are never treated as satisfied; they are reported.
A planned course's future grade is unknown, so a minimum-grade prerequisite on
a planned course becomes an explicit contingency instead of blocking the plan.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional, Union

from ortools.sat.python import cp_model

from ..models import GRADE_POINTS, Course, Program, Requirement, Requisite
from ..policy import BA_SUBJECT_CAP_EXEMPT, POLICIES_2026_2027
from ..store import CatalogStore, get_store
from ..terms import Term, catalog_year_for_entry, regular_semesters_between, term_range
from .schemas import (CompletedCourse, Infeasibility, Issue, Plan, PlannedCourse, PlannedTerm,
                      PlanRequest, PlanResponse, RequirementStatus)
from .validate import assumed_grade_sources, requisite_holds, validate_schedule

Lit = Union[bool, cp_model.IntVar]
UNITS = 2                                   # half-hour units per credit hour
MAX_PLANNING_TERMS = 16
NOT_AUTO_SELECTED_TITLE = re.compile(
    r"\btopics?\b|independent study|directed (?:reading|study)|thesis|internship|honors|seminar in", re.I)
TOTAL_HOURS = POLICIES_2026_2027["min_total_hours"].value
BA_CAP = POLICIES_2026_2027["ba_subject_cap"].value
DEGREE_URL = POLICIES_2026_2027["min_total_hours"].source_url


class PlanningError(ValueError):
    """Invalid request (bad term, unknown program...). Returned to clients as HTTP 422."""


def grade_ok(grade: Optional[str], minimum: Optional[str]) -> tuple[bool, bool]:
    """(meets, assumed): unknown/non-letter grades are assumed to meet the minimum, but flagged."""
    if not minimum:
        return True, False
    if grade is None or grade not in GRADE_POINTS:
        return True, True
    return GRADE_POINTS[grade] >= GRADE_POINTS[minimum], False


def hours(units: int) -> float:
    value = units / UNITS
    return int(value) if value == int(value) else value


# =========================================================== request context
@dataclass
class Context:
    store: CatalogStore
    request: PlanRequest
    programs: list[Program]
    terms: list[Term]
    entry: Term
    done: dict[str, CompletedCourse]
    extra_credit: list[tuple[str, float, str]]          # (code, hours, subject) for courses not in catalog
    tokens: set[str]
    locks: dict[str, int]
    candidates: dict[str, Course] = field(default_factory=dict)
    schedulable: dict[str, Course] = field(default_factory=dict)
    retakes: set[str] = field(default_factory=set)
    issues: list[Issue] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        return [t.label for t in self.terms]

    def units(self, code: str) -> int:
        """Credit hours of `code` in half-hour units. Variable-credit courses use their minimum."""
        course = self.store.courses.get(code)
        return round(course.credits_min * UNITS) if course else 0

    def term_bounds(self, term: Term) -> tuple[int, int]:
        if term.is_summer:
            return 0, self.request.summer_max_credits * UNITS
        return self.request.min_credits * UNITS, self.request.max_credits * UNITS


def _requisite_courses(node: Optional[Requisite]) -> list[tuple[str, Optional[str]]]:
    if node is None:
        return []
    if node.kind == "course":
        return [(node.code, node.min_grade)]
    if node.kind in ("all", "any"):
        return [x for item in node.items for x in _requisite_courses(item)]
    return []


def _token_nodes(node: Optional[Requisite]) -> list[str]:
    if node is None:
        return []
    if node.kind in ("placement", "permission"):
        return [node.token]
    if node.kind in ("all", "any"):
        return [t for i in node.items for t in _token_nodes(i)]
    return []


def _iter_nodes(nodes: list[Requirement]):
    for n in nodes:
        yield n
        yield from _iter_nodes(n.children)


def prepare(request: PlanRequest, store: Optional[CatalogStore] = None) -> Context:
    try:
        store = store or get_store(request.catalog_year)
    except FileNotFoundError as exc:
        raise PlanningError(f"Catalog year {request.catalog_year} is not available") from exc
    issues: list[Issue] = []

    if len(set(request.programs)) != len(request.programs):
        raise PlanningError("A program was selected twice")
    programs = []
    for pid in request.programs:
        program = store.program(pid)
        if program is None:
            listing = store.listings.get(pid)
            if listing is None:
                raise PlanningError(f"Unknown program: {pid}")
            raise PlanningError(f"{listing.name} does not have reviewed requirements yet, so it cannot be planned in this version.")
        programs.append(program)
    majors = sum(p.kind == "major" for p in programs)
    minors = sum(p.kind == "minor" for p in programs)
    if not (1 <= majors <= 2 and minors <= POLICIES_2026_2027["max_minors"].value and len(programs) <= 3):
        raise PlanningError("UNC allows one or two majors and up to two minors, at most three programs in total")
    if len({p.concentration_of or p.id for p in programs if p.kind == "major"}) < majors:
        raise PlanningError("Two concentrations/tracks of the same major cannot be combined")

    try:
        entry = Term.parse(request.entry_term)
        first = Term.parse(request.first_term)
        grad = Term.parse(request.graduation_term)
    except ValueError as exc:
        raise PlanningError(str(exc)) from exc
    if first < entry:
        raise PlanningError("The first planning term cannot be before your entry term")
    if grad.is_summer:
        raise PlanningError("Choose a Fall or Spring graduation term")
    if grad < first:
        raise PlanningError("The graduation term is before the first planning term")
    terms = term_range(first, grad, include_summer=request.include_summer)
    if len(terms) > MAX_PLANNING_TERMS:
        raise PlanningError(f"Plan at most {MAX_PLANNING_TERMS} terms at once")
    if request.min_credits > request.max_credits:
        raise PlanningError("Minimum credits per term exceed the maximum")

    governing = catalog_year_for_entry(entry)
    if governing != request.catalog_year:
        issues.append(Issue(severity="warning", code="catalog_year_mismatch",
                            message=f"You entered in {entry.label}, so the {governing} catalog normally governs your "
                                    f"requirements. This plan uses {request.catalog_year} requirements because older "
                                    "editions are not loaded yet; differences are possible."))
    if request.max_credits > POLICIES_2026_2027["term_max_hours"].value:
        issues.append(Issue(severity="warning", code="overload",
                            message="More than 18 hours in a semester needs a qualifying GPA or dean approval.",
                            source_url=POLICIES_2026_2027["term_max_hours"].source_url))
    if request.min_credits < POLICIES_2026_2027["term_min_hours"].value:
        issues.append(Issue(severity="warning", code="underload",
                            message="Fewer than 12 hours in a Fall/Spring semester needs dean permission.",
                            source_url=POLICIES_2026_2027["term_min_hours"].source_url))

    done: dict[str, CompletedCourse] = {}
    extra: list[tuple[str, float, str]] = []
    for item in request.completed:
        code = store.canonical(item.code)
        if code not in store.courses:
            if item.credits:
                extra.append((code, item.credits, code.split()[0] if " " in code else "OTHER"))
                issues.append(Issue(severity="info", code="course_not_in_catalog", course=code,
                                    message=f"{code} is not in the {request.catalog_year} catalog; counted as {item.credits:g} credit hours only."))
            else:
                issues.append(Issue(severity="warning", code="course_not_in_catalog", course=code,
                                    message=f"{code} is not in the {request.catalog_year} catalog and no credit hours were given, so it was ignored."))
            continue
        if item.grade == "F":
            issues.append(Issue(severity="info", code="failed_course", course=code,
                                message=f"{code} with grade F earns no credit and does not satisfy requirements."))
            continue
        prior = done.get(code)
        if prior is None or GRADE_POINTS.get(item.grade or "", -1) > GRADE_POINTS.get(prior.grade or "", -1):
            done[code] = item.model_copy(update={"code": code})

    tokens = {re.sub(r"\s+", " ", t.strip().upper()) for t in request.tokens}
    labels = [t.label for t in terms]
    locks: dict[str, int] = {}
    for lock in request.locks:
        code = store.canonical(lock.code)
        if code not in store.courses:
            raise PlanningError(f"Locked course {lock.code} is not in the catalog")
        if lock.term not in labels:
            raise PlanningError(f"Locked term {lock.term} is not one of the planning terms")
        locks[code] = labels.index(lock.term)

    ctx = Context(store, request, programs, terms, entry, done, extra, tokens, locks, issues=issues)
    _select_candidates(ctx)
    return ctx


def _select_candidates(ctx: Context) -> None:
    store = ctx.store
    excluded = {store.canonical(c) for c in ctx.request.exclude}
    selected_ids = set(ctx.request.programs)
    seeds: set[str] = set(ctx.locks)
    for program in ctx.programs:
        for node in _iter_nodes(program.requirements):
            if node.kind == "course" and node.course:
                seeds |= store.equivalents(node.course)
            for opt in node.conditional_options:
                if opt.requires_program in selected_ids:
                    seeds.add(opt.course)
            if node.kind == "filter" and node.filter:
                limit = node.filter.suggest_below
                seeds |= {c.code for c in store.matching(node.filter) if limit is None or c.number_int < limit}
            for bundle in node.bundles:
                seeds |= set(bundle)
    # Prerequisite closure through every alternative, tracking the highest
    # minimum grade any candidate demands of each course (for retake detection).
    thresholds: dict[str, str] = {}
    frontier, seen, depth = [c for c in seeds if c in store.courses], set(), 0
    while frontier and depth < 8:
        nxt = []
        for code in frontier:
            if code in seen:
                continue
            seen.add(code)
            course = store.courses[code]
            for req_code, minimum in _requisite_courses(course.prerequisites) + _requisite_courses(course.corequisites):
                if minimum and GRADE_POINTS[minimum] > GRADE_POINTS.get(thresholds.get(req_code, "F"), 0):
                    thresholds[req_code] = minimum
                nxt += [e for e in store.equivalents(req_code) if e in store.courses and e not in seen]
        frontier, depth = nxt, depth + 1
    for program in ctx.programs:
        for node in _iter_nodes(program.requirements):
            if node.min_grade and node.course:
                thresholds[node.course] = node.min_grade
    ctx.candidates = {c: store.courses[c] for c in seen}
    for code, course in ctx.candidates.items():
        record = ctx.done.get(code)
        if record is not None:
            if record.in_progress or grade_ok(record.grade, thresholds.get(code))[0]:
                continue
            ctx.retakes.add(code)
        if code in excluded:
            continue
        if code in ctx.locks:
            ctx.schedulable[code] = course
            continue
        # Auto-selected courses must be ordinary, fixed-credit undergraduate courses.
        if course.variable_credit or course.credits_min == 0 or course.number_int >= 700:
            continue
        if course.number.endswith("H") or NOT_AUTO_SELECTED_TITLE.search(course.title):
            continue
        ctx.schedulable[code] = course
    for code in ctx.locks:
        if code in ctx.done and code not in ctx.retakes:
            raise PlanningError(f"{code} is already completed and cannot be locked into a future term")


# ================================================================== the model
class PlanModel:
    def __init__(self, ctx: Context, *, assumptions: bool = False):
        self.ctx = ctx
        self.m = cp_model.CpModel()
        self.use_assumptions = assumptions
        self.assumption_lits: dict[int, str] = {}
        self.notes_by_course: dict[str, set[str]] = {}
        self._cache: dict = {}
        self.usage: dict[str, dict[str, list[tuple[str, cp_model.IntVar]]]] = {}
        self.node_sat: dict[tuple[str, str], Optional[Lit]] = {}
        n = len(ctx.terms)
        self.x = {c: [self.m.NewBoolVar(f"x[{c},{t}]") for t in range(n)] for c in ctx.schedulable}
        self.planned: dict[str, cp_model.IntVar] = {}
        for c, xs in self.x.items():
            p = self.m.NewBoolVar(f"planned[{c}]")
            self.m.Add(p == sum(xs))           # also enforces "at most once"
            self.planned[c] = p
        self._prerequisites()
        self._requirements()
        self._credits()
        self._locks()

    # ---------------------------------------------------------- helpers
    def _enforce(self, lit: Lit, explanation: str) -> None:
        """Require `lit`; when diagnosing, through a named assumption literal."""
        if self.use_assumptions:
            a = self.m.NewBoolVar(explanation)
            self.assumption_lits[a.Index()] = explanation
            if lit is False:
                self.m.Add(a == 0)
            elif lit is not True:
                self.m.AddImplication(a, lit)
            self.m.AddAssumption(a)
        elif lit is False:
            self.m.AddBoolOr([])               # unsatisfiable
        elif lit is not True:
            self.m.Add(lit == 1)

    def _or(self, lits: list[Lit]) -> Lit:
        if any(l is True for l in lits):
            return True
        vs = [l for l in lits if l is not False]
        if not vs:
            return False
        if len(vs) == 1:
            return vs[0]
        b = self.m.NewBoolVar("")
        self.m.AddMaxEquality(b, vs)
        return b

    def _and(self, lits: list[Lit]) -> Lit:
        if any(l is False for l in lits):
            return False
        vs = [l for l in lits if l is not True]
        if not vs:
            return True
        if len(vs) == 1:
            return vs[0]
        b = self.m.NewBoolVar("")
        self.m.AddMinEquality(b, vs)
        return b

    def _taken_by(self, code: str, t: int, inclusive: bool) -> Lit:
        key = ("by", code, t, inclusive)
        if key not in self._cache:
            self._cache[key] = self._or(list(self.x.get(code, [])[: t + 1 if inclusive else t]))
        return self._cache[key]

    def _atom(self, code: str, minimum: Optional[str], t: int, inclusive: bool) -> Lit:
        lits: list[Lit] = []
        for e in self.ctx.store.equivalents(code):
            record = self.ctx.done.get(e)
            if record is not None and e not in self.ctx.retakes and grade_ok(record.grade, minimum)[0]:
                return True
            lits.append(self._taken_by(e, t, inclusive))
        return self._or(lits)

    def requisite_lit(self, node: Optional[Requisite], t: int, for_course: str, in_any: bool = False) -> Lit:
        if node is None:
            return True
        key = ("req", id(node), t, in_any)
        if key in self._cache:
            return self._cache[key]
        if node.kind == "course":
            lit = self._atom(node.code, node.min_grade, t, node.concurrent_ok)
        elif node.kind == "all":
            lit = self._and([self.requisite_lit(i, t, for_course) for i in node.items])
        elif node.kind == "any":
            lit = self._or([self.requisite_lit(i, t, for_course, True) for i in node.items])
        elif node.kind in ("placement", "permission"):
            lit = node.token in self.ctx.tokens
        elif in_any:
            lit = False      # an unmodeled condition never stands in for a real alternative
        else:
            lit = True       # a required unmodeled condition is flagged on the course, not assumed silently
            self.notes_by_course.setdefault(for_course, set()).add(
                f"Also requires: {node.text} (not checked by the planner)")
        self._cache[key] = lit
        return lit

    # ------------------------------------------------------ constraints
    def _prerequisites(self) -> None:
        for code, xs in self.x.items():
            course = self.ctx.schedulable[code]
            for t, var in enumerate(xs):
                for tree in (course.prerequisites, course.corequisites):
                    lit = self.requisite_lit(tree, t, code)
                    if lit is False:
                        self.m.Add(var == 0)
                    elif lit is not True:
                        self.m.AddImplication(var, lit)

    def avail(self, code: str, minimum: Optional[str]) -> Lit:
        """Exactly `code` is completed with an adequate grade, or planned. Cross-listings
        are separate options so the plan reports the code actually taken."""
        record = self.ctx.done.get(code)
        if record is not None and code not in self.ctx.retakes and grade_ok(record.grade, minimum)[0]:
            return True
        return self.planned.get(code, False)

    def _use(self, program: Program, node_id: str, codes: tuple[str, ...], lit: Lit) -> Optional[cp_model.IntVar]:
        if lit is False:
            return None
        u = self.m.NewBoolVar(f"u[{node_id},{'+'.join(codes)}]")
        if lit is not True:
            self.m.AddImplication(u, lit)
        for code in codes:
            self.usage.setdefault(program.id, {}).setdefault(code, []).append((node_id, u))
        return u

    def _compile(self, program: Program, node: Requirement) -> Optional[Lit]:
        store = self.ctx.store
        selected = set(self.ctx.request.programs)
        sat: Optional[Lit] = None
        if node.kind == "course":
            options = sorted(store.equivalents(node.course))
            options += [o.course for o in node.conditional_options if o.requires_program in selected]
            uses = [u for o in options
                    if (u := self._use(program, node.id, (o,), self.avail(o, node.min_grade))) is not None]
            if uses:
                sat = self.m.NewBoolVar(f"sat[{node.id}]")
                self.m.Add(sat == sum(uses))   # at most one option is used
            else:
                sat = False
        elif node.kind == "all":
            subs = [self._compile(program, c) for c in node.children]
            sat = self._and([s for s in subs if s is not None])
        elif node.kind == "choose":
            subs = [s for s in (self._compile(program, c) for c in node.children) if s is not None]
            need = node.count or 1
            live = [s for s in subs if s is not False]
            if len(live) < need:
                sat = False
            else:
                sat = self.m.NewBoolVar(f"sat[{node.id}]")
                self.m.Add(sum(1 if s is True else s for s in live) >= need).OnlyEnforceIf(sat)
        elif node.kind == "filter":
            uses: list[tuple[cp_model.IntVar, int]] = []
            options = sorted({e for course in store.matching(node.filter) for e in store.equivalents(course.code)})
            for code in options:
                u = self._use(program, node.id, (code,), self.avail(code, node.min_grade))
                if u is not None:
                    uses.append((u, self.ctx.units(code)))
            for bundle in node.bundles:   # e.g. three labs that together count as ONE course
                u = self._use(program, node.id, tuple(bundle),
                              self._and([self.avail(c, node.min_grade) for c in bundle]))
                if u is not None:
                    uses.append((u, sum(self.ctx.units(c) for c in bundle)))
            if len(uses) < (node.count or 0):
                sat = False
            else:
                sat = self.m.NewBoolVar(f"sat[{node.id}]")
                self.m.Add(sum(u for u, _ in uses) >= (node.count or 0)).OnlyEnforceIf(sat)
                if node.min_hours:
                    self.m.Add(sum(u * cr for u, cr in uses) >= node.min_hours * UNITS).OnlyEnforceIf(sat)
        # kind == "unresolved": sat stays None -> reported as uncertain, never counted as satisfied
        self.node_sat[(program.id, node.id)] = sat
        return sat

    def _requirements(self) -> None:
        for program in self.ctx.programs:
            for top in program.requirements:
                children = top.children if top.kind == "all" and top.children else [top]
                for child in children:
                    sat = self._compile(program, child)
                    if sat is not None:
                        self._enforce(sat, f"{program.name}: {top.label} - {child.label}")
                if top.kind == "all" and top.children:
                    subs = [self.node_sat[(program.id, c.id)] for c in top.children]
                    self.node_sat[(program.id, top.id)] = self._and([s for s in subs if s is not None])
            for code, uses in self.usage.get(program.id, {}).items():
                distinct = {u.Index(): u for _, u in uses}
                if len(distinct) > 1:
                    self.m.Add(sum(distinct.values()) <= 1)

    def _credits(self) -> None:
        ctx, m = self.ctx, self.m
        self.course_units: list = []
        self.filler: list[cp_model.IntVar] = []
        for t, term in enumerate(ctx.terms):
            lo, hi = ctx.term_bounds(term)
            cc = sum(ctx.units(c) * xs[t] for c, xs in self.x.items())
            filler = m.NewIntVar(0, hi, f"unassigned[{t}]")
            m.Add(cc + filler <= hi)
            m.Add(cc + filler >= lo)
            self.course_units.append(cc)
            self.filler.append(filler)
        self.ba = any(p.degree == "BA" for p in ctx.programs if p.kind == "major")
        constant: dict[str, int] = {}
        for code in ctx.done:
            subject = "EXEMPT" if code in BA_SUBJECT_CAP_EXEMPT else code.split()[0]
            constant[subject] = constant.get(subject, 0) + ctx.units(code)
        for _, cr, subject in ctx.extra_credit:
            constant[subject] = constant.get(subject, 0) + round(cr * UNITS)
        planned: dict[str, list] = {}
        for code, xs in self.x.items():
            if code in ctx.retakes:
                continue        # a repeated course's hours count once (already in `constant`)
            subject = "EXEMPT" if code in BA_SUBJECT_CAP_EXEMPT else code.split()[0]
            planned.setdefault(subject, []).append(ctx.units(code) * sum(xs))
        countable = []
        for subject in sorted(set(constant) | set(planned)):
            expr = constant.get(subject, 0) + sum(planned.get(subject, []))
            if self.ba and subject != "EXEMPT":
                raw = m.NewIntVar(0, 1000, f"subject[{subject}]")
                m.Add(raw == expr)
                capped = m.NewIntVar(0, BA_CAP * UNITS, f"countable[{subject}]")
                m.AddMinEquality(capped, [raw, BA_CAP * UNITS])
                countable.append(capped)
            else:
                countable.append(expr)
        self.countable_units = sum(countable)
        total_ok = m.NewBoolVar("total")
        m.Add(self.countable_units + sum(self.filler) >= TOTAL_HOURS * UNITS).OnlyEnforceIf(total_ok)
        self._enforce(total_ok, f"Reach {TOTAL_HOURS} credit hours by graduation within the per-term credit limits")

    def _locks(self) -> None:
        for code, t in self.ctx.locks.items():
            self._enforce(self.x[code][t], f"Your lock: {code} in {self.ctx.labels[t]}")

    def objective(self) -> None:
        ctx, m = self.ctx, self.m
        planned_units = sum(ctx.units(c) * sum(xs) for c, xs in self.x.items())
        # Soft per-term target for program coursework, leaving room for Gen Eds.
        target = ctx.request.target_program_credits * UNITS
        excess = []
        for t, term in enumerate(ctx.terms):
            if not term.is_summer:
                over = m.NewIntVar(0, 30 * UNITS, f"over_target[{t}]")
                m.Add(over >= self.course_units[t] - target)
                excess.append(over)
        # Named requirements and the prerequisites behind them are pulled earlier
        # than interchangeable electives (weight 2 vs 1).
        elective_only = self._elective_only_codes()
        earliness = sum((1 if c in elective_only else 2) * t * ctx.units(c) * xs[t]
                        for c, xs in self.x.items() for t in range(len(xs)))
        summer = sum(ctx.units(c) * xs[t] for c, xs in self.x.items()
                     for t, term in enumerate(ctx.terms) if term.is_summer)
        # Prefer the code a requirement names over a cross-listed twin (MATH 235 over STOR 235).
        named = self._named_codes()
        indirect = sum(sum(xs) for c, xs in self.x.items() if c not in named)
        registrations = sum(sum(xs) for xs in self.x.values())
        # Lexicographic: fewest extra course hours, then stay near the per-term
        # target, then avoid summers, then fewer separate courses (e.g. a 3-credit
        # elective over three 1-credit labs), then named codes, then earlier.
        m.Minimize(1_000_000 * planned_units + 20_000 * sum(excess) + 5_000 * summer
                   + 3_000 * registrations + 200 * indirect + earliness)

    def _elective_only_codes(self) -> set[str]:
        filtered, named = set(), set()
        for program in self.ctx.programs:
            for node in _iter_nodes(program.requirements):
                if node.kind == "filter" and node.filter:
                    filtered |= {c.code for c in self.ctx.store.matching(node.filter)}
                elif node.kind == "course" and node.course:
                    named.add(node.course)
        return filtered - named

    def _named_codes(self) -> set[str]:
        named: set[str] = set()
        for program in self.ctx.programs:
            for node in _iter_nodes(program.requirements):
                if node.kind == "course" and node.course:
                    named.add(node.course)
                if node.kind == "filter" and node.filter:
                    named |= {c.code for c in self.ctx.store.matching(node.filter)}
                for bundle in node.bundles:
                    named |= set(bundle)
        return named


# ================================================================== solving
def _solver(seconds: float = 10.0) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = 7
    return solver


def _solve(ctx: Context, alternatives: int = 1):
    pm = PlanModel(ctx)
    pm.objective()
    solutions, statuses = [], []
    for _ in range(alternatives):
        solver = _solver()
        status = solver.Solve(pm.m)
        statuses.append(solver.StatusName(status))
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        chosen = [(c, t) for c, xs in pm.x.items() for t, v in enumerate(xs) if solver.Value(v)]
        result = _extract(pm, solver, chosen)
        result.objective = solver.ObjectiveValue()
        solutions.append(result)
        if not chosen:
            break
        pm.m.Add(sum(pm.x[c][t] for c, t in chosen) <= len(chosen) - 1)   # next: a different schedule
    return pm, solutions, statuses


def plan(request: PlanRequest, store: Optional[CatalogStore] = None) -> PlanResponse:
    started = time.perf_counter()
    ctx = prepare(request, store)
    pm, solutions, statuses = _solve(ctx, request.alternatives)
    response = PlanResponse(
        status="feasible" if solutions else "infeasible",
        catalog_year=request.catalog_year,
        programs=[{"id": p.id, "name": p.name, "kind": p.kind, "degree": p.degree, "url": p.url,
                   "verification": p.verification.model_dump()} for p in ctx.programs],
        plans=solutions, issues=list(ctx.issues), not_modeled=_not_modeled(ctx))
    if solutions:
        response.issues += _plan_issues(solutions[0])
    else:
        response.infeasibility = diagnose(ctx) if request.diagnose else Infeasibility(
            summary="No plan satisfies all constraints.", causes=[], suggestions=[])
    response.issues += _requirement_issues(ctx)
    response.solver = {"engine": "OR-Tools CP-SAT", "statuses": statuses,
                       "candidate_courses": len(ctx.candidates), "schedulable_courses": len(ctx.schedulable),
                       "variables": len(pm.m.Proto().variables),
                       "seconds": round(time.perf_counter() - started, 3)}
    return response


# ============================================================ result building
def _extract(pm: PlanModel, solver: cp_model.CpSolver, chosen: list[tuple[str, int]]) -> Plan:
    ctx = pm.ctx
    by_term: dict[int, list[str]] = {}
    for c, t in chosen:
        by_term.setdefault(t, []).append(c)
    planned_term = dict(chosen)
    problems = validate_schedule(ctx, planned_term)
    if problems:   # the CP-SAT encoding and the independent checker disagree: never return this plan
        raise AssertionError("Internal plan validation failed: " + "; ".join(problems))
    nodes = {(p.id, n.id): (p, n) for p in ctx.programs for n in _iter_nodes(p.requirements)}
    used_by: dict[str, list[tuple[str, str]]] = {}
    for pid, codes in pm.usage.items():
        for code, uses in codes.items():
            for node_id, u in uses:
                if solver.Value(u):
                    used_by.setdefault(code, []).append((pid, node_id))

    course_units = [sum(ctx.units(c) for c in by_term.get(t, [])) for t in range(len(ctx.terms))]
    filler = _distribute_unassigned(ctx, course_units, solver.Value(pm.countable_units))
    terms_out = []
    for t, term in enumerate(ctx.terms):
        courses = []
        for code in sorted(by_term.get(t, []), key=lambda c: (c.split()[0], ctx.store.courses[c].number_int)):
            course = ctx.store.courses[code]
            reasons, req_ids = [], []
            for pid, node_id in used_by.get(code, []):
                program, node = nodes[(pid, node_id)]
                reasons.append(f"{program.name}: {node.label}")
                req_ids.append(node_id)
            unlocks = sorted(other for other in planned_term if other != code and code in
                             {e for rc, _ in _requisite_courses(ctx.store.courses[other].prerequisites)
                              + _requisite_courses(ctx.store.courses[other].corequisites)
                              for e in ctx.store.equivalents(rc)})
            if unlocks:
                reasons.append("Prerequisite for " + ", ".join(unlocks))
            if code in ctx.retakes:
                reasons.append("Retake: completed grade is below a required minimum")
            if code in ctx.locks:
                reasons.append("You locked this course into this term")
            courses.append(PlannedCourse(
                code=code, title=course.title, credits=hours(ctx.units(code)), reasons=reasons or ["Supports another planned course"],
                requirement_ids=req_ids, contingencies=_contingencies(ctx, code, t, planned_term),
                warnings=_course_warnings(ctx, pm, course, term, planned_term), requisites_status=course.requisites_status,
                gen_ed=course.gen_ed, source_url=course.source.url))
        terms_out.append(PlannedTerm(term=term.label, courses=courses, course_credits=hours(course_units[t]),
                                     unassigned_credits=hours(filler[t]),
                                     total_credits=hours(course_units[t] + filler[t])))

    trees = {p.id: [_status_tree(pm, solver, p, n, planned_term) for n in p.requirements] for p in ctx.programs}
    return Plan(terms=terms_out, requirements=trees,
                summary=_summary(ctx, pm, solver, terms_out, used_by, sum(filler)))


def _distribute_unassigned(ctx: Context, course_units: list[int], countable_units: int) -> list[int]:
    """Spread placeholder Gen Ed/elective hours so each term meets its minimum,
    stays under its maximum, terms are as even as possible, and the degree
    reaches 120 hours. Summers are used only if regular terms are full."""
    lo, hi = [], []
    for t, term in enumerate(ctx.terms):
        floor, cap = ctx.term_bounds(term)
        lo.append(max(0, floor - course_units[t]))
        hi.append(max(0, cap - course_units[t]))
    filler = list(lo)
    remaining = TOTAL_HOURS * UNITS - countable_units - sum(filler)
    step = UNITS  # whole hours
    while remaining > 0:
        options = [t for t in range(len(ctx.terms)) if filler[t] + step <= hi[t]]
        if not options:
            break
        regular = [t for t in options if not ctx.terms[t].is_summer]
        t = min(regular or options, key=lambda i: (course_units[i] + filler[i], i))
        filler[t] += step
        remaining -= step
    return filler


def _contingencies(ctx: Context, code: str, t: int, planned_term: dict[str, int]) -> list[str]:
    out = []
    for req_code, minimum in _requisite_courses(ctx.store.courses[code].prerequisites):
        if minimum:
            for e in ctx.store.equivalents(req_code):
                if e in planned_term and planned_term[e] < t:
                    out.append(f"Needs a grade of {minimum} or better in {e} ({ctx.labels[planned_term[e]]})")
    return sorted(set(out))


def _course_warnings(ctx: Context, pm: PlanModel, course: Course, term: Term, schedule: dict[str, int]) -> list[str]:
    out = sorted(pm.notes_by_course.get(course.code, set()))
    if course.requisites_status in ("partial", "unparsed", "needs_reverification"):
        out.append(f"Requisite text not fully interpreted ({course.requisites_status}): \"{course.requisites_raw}\"")
    if term.is_summer:
        out.append("Summer availability of this course is not verified")
    used_tokens = [tok for tok in _token_nodes(course.prerequisites) if tok in ctx.tokens]
    if used_tokens:
        out.append("Relies on your placement/permission: " + ", ".join(sorted(set(used_tokens))))
    t = ctx.labels.index(term.label)
    for tree in (course.prerequisites, course.corequisites):
        # Warn only when the plan actually depends on a grade we have not seen.
        if not requisite_holds(ctx, tree, t, schedule, allow_assumed=False):
            for done_code, minimum in sorted(set(assumed_grade_sources(ctx, tree))):
                out.append(f"Assumes your {done_code} grade is {minimum} or better (no grade entered)")
    return out


def _status_tree(pm: PlanModel, solver: cp_model.CpSolver, program: Program, node: Requirement,
                 planned_term: dict[str, int]) -> RequirementStatus:
    ctx = pm.ctx
    children = [_status_tree(pm, solver, program, c, planned_term) for c in node.children]
    courses = []
    for code, uses in pm.usage.get(program.id, {}).items():
        for node_id, u in uses:
            if node_id == node.id and solver.Value(u):
                term = planned_term.get(code)
                courses.append({"code": code, "term": ctx.labels[term] if term is not None else None,
                                "completed": term is None})
    sat = pm.node_sat.get((program.id, node.id))
    satisfied = sat is True or (sat is not None and sat is not False and bool(solver.Value(sat)))
    rank = {"unmet": 4, "uncertain": 3, "planned": 2, "completed": 1, "not_needed": 0}
    if node.kind == "unresolved":
        status = "uncertain"
    elif node.kind in ("course", "filter"):
        status = ("completed" if all(c["completed"] for c in courses) else "planned") if satisfied and courses else "unmet"
    elif node.kind == "choose":
        met = [c for c in children if c.status in ("completed", "planned")]
        need = node.count or 1
        if len(met) >= need:
            status = "completed" if sum(c.status == "completed" for c in met) >= need else "planned"
            for c in children:
                if c.status == "unmet":
                    _mark_not_needed(c)
        else:
            status = "uncertain" if any(c.status == "uncertain" for c in children) else "unmet"
    else:
        status = max((c.status for c in children), key=lambda s: rank[s], default="completed")
    return RequirementStatus(
        id=node.id, label=node.label, kind=node.kind, status=status, courses=courses, core=node.core,
        min_hours=node.min_hours, count=node.count,
        source=node.source.model_dump(exclude_none=True), verification=node.verification.model_dump(),
        children=children)


def _mark_not_needed(node: RequirementStatus) -> None:
    node.status = "not_needed"
    for c in node.children:
        _mark_not_needed(c)


def _summary(ctx: Context, pm: PlanModel, solver: cp_model.CpSolver, terms_out: list[PlannedTerm],
             used_by: dict[str, list[tuple[str, str]]], filler_units: int) -> dict:
    completed_units = sum(ctx.units(c) for c in ctx.done) + sum(round(cr * UNITS) for _, cr, _ in ctx.extra_credit)
    planned_units = sum(ctx.units(c.code) for t in terms_out for c in t.courses)
    unc_completed = sum(ctx.units(c) for c, r in ctx.done.items() if r.origin == "unc")
    transfer_units = sum(ctx.units(c) for c, r in ctx.done.items() if r.origin == "transfer") + \
        sum(round(cr * UNITS) for _, cr, _ in ctx.extra_credit)
    subject_units: dict[str, int] = {}
    for code in list(ctx.done) + [c.code for t in terms_out for c in t.courses]:
        if code not in BA_SUBJECT_CAP_EXEMPT:
            subject_units[code.split()[0]] = subject_units.get(code.split()[0], 0) + ctx.units(code)
    core = {}
    for program in ctx.programs:
        if program.kind != "major":
            continue
        core_ids = {n.id for n in _iter_nodes(program.requirements) if n.core}
        codes = {c for c, uses in used_by.items() for pid, nid in uses if pid == program.id and nid in core_ids}
        at_unc = [c for c in codes if c not in ctx.done or ctx.done[c].origin == "unc"]
        by_exam = [c for c in codes if c in ctx.done and ctx.done[c].origin == "exam"]
        core_units = sum(ctx.units(c) for c in codes)
        unc_units = sum(ctx.units(c) for c in at_unc)
        core[program.id] = {
            "core_courses": sorted(codes), "core_courses_at_unc_projected": len(at_unc),
            "core_hours": hours(core_units), "core_hours_at_unc_projected": hours(unc_units),
            "half_at_unc_ok": 2 * len(at_unc) >= len(codes) and 2 * unc_units >= core_units,
            "by_exam_core_courses": sorted(by_exam), "by_exam_limit_ok": len(by_exam) <= 2}
    last = ctx.terms[-1] if ctx.terms else ctx.entry
    return {
        "completed_hours": hours(completed_units),
        "planned_course_hours": hours(planned_units),
        "unassigned_gen_ed_elective_hours": hours(filler_units),
        "projected_total_hours": hours(completed_units + planned_units + filler_units),
        "countable_hours_after_ba_cap": hours(solver.Value(pm.countable_units) + filler_units),
        "ba_subject_cap_applies": pm.ba,
        "subjects_over_45_hours": sorted(s for s, u in subject_units.items() if u > BA_CAP * UNITS) if pm.ba else [],
        "unc_hours_projected": hours(unc_completed + planned_units + filler_units),
        "transfer_hours": hours(transfer_units),
        "regular_semesters_entry_to_graduation": regular_semesters_between(ctx.entry, last),
        "major_core": core,
        "graduation_term": ctx.labels[-1] if ctx.labels else None,
    }


def _plan_issues(plan_: Plan) -> list[Issue]:
    issues, s = [], plan_.summary
    eight = POLICIES_2026_2027["eight_semesters"]
    if s["regular_semesters_entry_to_graduation"] > eight.value:
        issues.append(Issue(severity="warning", code="ninth_semester", source_url=eight.source_url,
                            message=f"This plan spans {s['regular_semesters_entry_to_graduation']} Fall/Spring semesters "
                                    "from your entry term; more than eight requires an approved petition "
                                    "(transfer students may have up to ten)."))
    if s["transfer_hours"] > POLICIES_2026_2027["max_transfer_hours"].value:
        issues.append(Issue(severity="warning", code="transfer_limit", source_url=DEGREE_URL,
                            message="More than 75 transfer hours entered; at most 75 count."))
    if s["unc_hours_projected"] < POLICIES_2026_2027["min_unc_hours"].value:
        issues.append(Issue(severity="blocker", code="unc_hours", source_url=DEGREE_URL,
                            message="Fewer than 45 hours are projected at UNC-Chapel Hill."))
    for core in s["major_core"].values():
        if not core["half_at_unc_ok"]:
            issues.append(Issue(severity="warning", code="core_residency", source_url=DEGREE_URL,
                                message="Less than half of the major core is projected at UNC-Chapel Hill."))
        if not core["by_exam_limit_ok"]:
            issues.append(Issue(severity="warning", code="core_by_exam", source_url=DEGREE_URL,
                                message="More than two by-exam courses are used in the major core."))
    if s["subjects_over_45_hours"]:
        issues.append(Issue(severity="info", code="ba_subject_cap", source_url=DEGREE_URL,
                            message="Hours above 45 in " + ", ".join(s["subjects_over_45_hours"]) +
                                    " do not count toward the 120 (B.A. rule); the plan accounts for this."))
    if any(t.unassigned_credits for t in plan_.terms):
        issues.append(Issue(severity="info", code="unassigned_hours",
                            source_url=POLICIES_2026_2027["ideas_gen_ed"].source_url,
                            message="'Gen Ed / elective' hours are placeholders that keep you full-time and reach 120 "
                                    "hours; fill them with IDEAs in Action courses chosen with your advisor."))
    issues.append(Issue(severity="warning", code="offerings_unverified",
                        message="Course offering terms are not modeled yet: every course is assumed available each "
                                "Fall and Spring. Check ConnectCarolina before registering."))
    return issues


def _requirement_issues(ctx: Context) -> list[Issue]:
    out = []
    for program in ctx.programs:
        if program.verification.status == "needs_reverification":
            out.append(Issue(severity="warning", code="program_changed", source_url=program.url,
                             message=f"The catalog text for {program.name} changed after it was verified; re-review pending."))
        for node in _iter_nodes(program.requirements):
            if node.kind == "unresolved":
                out.append(Issue(severity="warning", code="uncertain_requirement", source_url=program.url,
                                 message=f"{program.name}: \"{node.label}\" could not be interpreted and is NOT planned or counted."))
    return out


def _not_modeled(ctx: Context) -> list[str]:
    items = ["IDEAs in Action General Education course-by-course assignment (placeholder hours are reserved instead)",
             "Term-by-term course offerings and seat availability",
             "GPA requirements (2.000 overall and in the major core), which depend on future grades"]
    if any(p.degree == "BA" for p in ctx.programs):
        items.append("B.A. Supplemental General Education")
    if len(ctx.programs) > 1:
        items.append("Cross-program core exclusivity (more than half of each core exclusive)")
    return items


# ================================================================= diagnosis
def diagnose(ctx: Context) -> Infeasibility:
    causes: list[str] = []
    pm = PlanModel(ctx, assumptions=True)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_workers = 1
    if solver.Solve(pm.m) == cp_model.INFEASIBLE:
        core = [pm.assumption_lits[i] for i in solver.SufficientAssumptionsForInfeasibility()
                if i in pm.assumption_lits]
        causes += [f"Conflicting requirement: {c}" for c in core]
    causes += _capacity_analysis(ctx)
    causes += _chain_analysis(ctx)
    summary = ("No schedule satisfies every requirement and prerequisite by "
               f"{ctx.labels[-1] if ctx.labels else 'the chosen term'} within the credit limits.")
    return Infeasibility(summary=summary,
                         causes=causes or ["The constraints conflict; try a later graduation term."],
                         suggestions=_relaxations(ctx))


def _capacity_analysis(ctx: Context) -> list[str]:
    """Can the remaining terms even hold enough hours to reach 120?"""
    completed = sum(ctx.units(c) for c in ctx.done) + sum(round(cr * UNITS) for _, cr, _ in ctx.extra_credit)
    capacity = sum(ctx.term_bounds(t)[1] for t in ctx.terms)
    if completed + capacity < TOTAL_HOURS * UNITS:
        return [f"Only {hours(completed + capacity)} credit hours are possible by {ctx.labels[-1]} "
                f"({hours(completed)} completed + at most {hours(capacity)} in {len(ctx.terms)} term(s)); "
                f"UNC requires {TOTAL_HOURS}."]
    return []


def _chain_analysis(ctx: Context) -> list[str]:
    """Earliest term index each course could be taken (ignoring credit limits);
    report required courses whose prerequisite chain is longer than the plan."""
    INF = 10 ** 6
    store = ctx.store
    earliest: dict[str, int] = {}
    via: dict[str, Optional[str]] = {}

    def done_ok(code: str, minimum: Optional[str]) -> bool:
        return any((r := ctx.done.get(e)) is not None and e not in ctx.retakes and grade_ok(r.grade, minimum)[0]
                   for e in store.equivalents(code))

    def ev(node, in_any=False) -> tuple[int, Optional[str]]:
        if node is None:
            return 0, None
        if node.kind == "course":
            if done_ok(node.code, node.min_grade):
                return 0, None
            best = (INF, None)
            for e in store.equivalents(node.code):
                if e in ctx.schedulable and earliest.get(e, INF) < INF:
                    best = min(best, (earliest[e] + (0 if node.concurrent_ok else 1), e))
            return best
        if node.kind == "all":
            return max((ev(i) for i in node.items), key=lambda v: v[0], default=(0, None))
        if node.kind == "any":
            return min((ev(i, True) for i in node.items), key=lambda v: v[0], default=(INF, None))
        if node.kind in ("placement", "permission"):
            return (0, None) if node.token in ctx.tokens else (INF, None)
        return (INF, None) if in_any else (0, None)

    for _ in range(40):
        changed = False
        for code, course in ctx.schedulable.items():
            value = max(ev(course.prerequisites), ev(course.corequisites), key=lambda v: v[0])
            if earliest.get(code) != value[0]:
                earliest[code], via[code] = value
                changed = True
        if not changed:
            break

    def chain(code: str) -> list[str]:
        out, seen = [code], {code}
        while via.get(out[-1]) and via[out[-1]] not in seen:
            out.append(via[out[-1]])
            seen.add(out[-1])
        return list(reversed(out))

    def course_earliest(code: str, minimum: Optional[str]) -> tuple[int, Optional[str]]:
        if done_ok(code, minimum):
            return -1, None
        options = [e for e in store.equivalents(code) if e in ctx.schedulable]
        return min(((earliest.get(e, INF), e) for e in options), default=(INF, code))

    def req_earliest(node: Requirement) -> tuple[int, Optional[str]]:
        """Earliest term index by which `node` can be complete, honoring its alternatives."""
        if node.kind == "course":
            return course_earliest(node.course, node.min_grade)
        if node.kind == "filter":
            vals = sorted(course_earliest(c.code, node.min_grade) for c in store.matching(node.filter))
            k = node.count or 1
            return vals[k - 1] if len(vals) >= k else (INF, None)
        if node.kind == "choose":
            vals = sorted(req_earliest(c) for c in node.children)
            k = node.count or 1
            return vals[k - 1] if len(vals) >= k else (INF, None)
        if node.kind == "all":
            return max((req_earliest(c) for c in node.children), default=(-1, None))
        return -1, None   # unresolved: not planned, reported elsewhere

    n, messages = len(ctx.terms), []
    for program in ctx.programs:
        for top in program.requirements:
            for node in (top.children if top.kind == "all" and top.children else [top]):
                e, code = req_earliest(node)
                if e >= INF:
                    tokens = sorted({t for t in _token_nodes(store.courses[code].prerequisites) if t not in ctx.tokens}) \
                        if code in store.courses else []
                    hint = f" Placement/permission ({', '.join(tokens)}) would also satisfy it." if tokens else ""
                    messages.append(f"{node.label}: {code} cannot be reached with the courses available.{hint}")
                elif e >= n:
                    messages.append(f"{node.label}: {code} needs {e + 1} terms because of its prerequisite chain "
                                    f"({' -> '.join(chain(code))}), but the plan has only {n} term(s).")
    return messages


def _relaxations(ctx: Context) -> list[str]:
    out: list[str] = []
    req = ctx.request
    grad = Term.parse(req.graduation_term)

    def feasible(**changes) -> bool:
        try:
            trial = prepare(req.model_copy(update={**changes, "alternatives": 1, "diagnose": False}), ctx.store)
        except PlanningError:
            return False
        return _solver(5).Solve(PlanModel(trial).m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    later = grad
    for _ in range(4):
        later = later.next()
        while later.is_summer:
            later = later.next()
        if feasible(graduation_term=later.label):
            out.append(f"Graduating in {later.label} instead of {grad.label} makes a plan possible.")
            break
    if not req.include_summer and feasible(include_summer=True):
        out.append("Adding summer terms makes a plan possible by your chosen graduation term.")
    if req.locks and feasible(locks=[]):
        out.append("Removing your course locks makes a plan possible.")
    if req.max_credits < 18 and feasible(max_credits=18):
        out.append("Allowing up to 18 credit hours per semester makes a plan possible.")
    placements = sorted({tok for course in ctx.schedulable.values() for tok in _token_nodes(course.prerequisites)
                         if tok.startswith("PLACEMENT:") and tok not in ctx.tokens})
    for tok in placements[:6]:
        if feasible(tokens=sorted(ctx.tokens | {tok})):
            out.append(f"Department placement into {tok.split(':', 1)[1]} (placement test or advisor) would make a plan possible by your chosen term.")
    if not out:
        out.append("No single change found a feasible plan; check completed courses, placements, and grades.")
    return out
