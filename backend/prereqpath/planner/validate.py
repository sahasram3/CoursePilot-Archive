"""Independent, solver-free checks of a finished schedule.

Used after every solve (a violation is a bug, never shown as a valid plan) and in
tests, so the CP-SAT encoding is cross-checked by a second implementation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..models import GRADE_POINTS, Requisite

if TYPE_CHECKING:
    from .engine import Context


def _grade_meets(grade: Optional[str], minimum: Optional[str], allow_assumed: bool) -> bool:
    if not minimum:
        return True
    if grade is None or grade not in GRADE_POINTS:
        return allow_assumed
    return GRADE_POINTS[grade] >= GRADE_POINTS[minimum]


def requisite_holds(ctx: "Context", node: Optional[Requisite], t: int, schedule: dict[str, int],
                    *, allow_assumed: bool, in_any: bool = False) -> bool:
    """Does `node` hold for a course taken in term index `t` under `schedule`?
    Completed courses with no recorded grade meet a minimum only if allow_assumed
    (by-exam credit always does). Unmodeled conditions never satisfy an alternative."""
    if node is None:
        return True
    if node.kind == "course":
        for e in sorted(ctx.store.equivalents(node.code)):
            record = ctx.done.get(e)
            if record is not None and e not in ctx.retakes and \
                    _grade_meets(record.grade, node.min_grade, allow_assumed or record.origin == "exam"):
                return True
            when = schedule.get(e)
            if when is not None and (when < t or (node.concurrent_ok and when == t)):
                return True
        return False
    if node.kind == "all":
        return all(requisite_holds(ctx, i, t, schedule, allow_assumed=allow_assumed) for i in node.items)
    if node.kind == "any":
        return any(requisite_holds(ctx, i, t, schedule, allow_assumed=allow_assumed, in_any=True) for i in node.items)
    if node.kind in ("placement", "permission"):
        return node.token in ctx.tokens
    return not in_any


def satisfiers(ctx: "Context", node: Optional[Requisite], t: int, schedule: dict[str, int]) -> list[str]:
    """The completed/earlier-planned courses (or placement tokens) that actually
    meet `node` for a course in term `t`; for OR, the first alternative that holds."""
    if node is None:
        return []
    if node.kind == "course":
        for e in sorted(ctx.store.equivalents(node.code)):
            record = ctx.done.get(e)
            if record is not None and e not in ctx.retakes and _grade_meets(record.grade, node.min_grade, True):
                return [e]
        for e in sorted(ctx.store.equivalents(node.code)):
            when = schedule.get(e)
            if when is not None and (when < t or (node.concurrent_ok and when == t)):
                return [e]
        return []
    if node.kind == "all":
        return [s for i in node.items for s in satisfiers(ctx, i, t, schedule)]
    if node.kind == "any":
        for item in node.items:
            if requisite_holds(ctx, item, t, schedule, allow_assumed=True, in_any=True):
                return satisfiers(ctx, item, t, schedule)
        return []
    if node.kind in ("placement", "permission"):
        return [node.token] if node.token in ctx.tokens else []
    return []


def assumed_grade_sources(ctx: "Context", node: Optional[Requisite]) -> list[tuple[str, str]]:
    """Completed courses in `node` whose minimum grade we can only assume (no grade entered)."""
    if node is None:
        return []
    if node.kind == "course":
        out = []
        for e in sorted(ctx.store.equivalents(node.code)):
            record = ctx.done.get(e)
            if node.min_grade and record is not None and record.origin != "exam" and \
                    (record.grade is None or record.grade not in GRADE_POINTS):
                out.append((e, node.min_grade))
        return out
    if node.kind in ("all", "any"):
        return [x for i in node.items for x in assumed_grade_sources(ctx, i)]
    return []


def validate_schedule(ctx: "Context", schedule: dict[str, int]) -> list[str]:
    """Return every rule the schedule breaks (empty list = consistent)."""
    problems = []
    units_by_term = [0] * len(ctx.terms)
    for code, t in schedule.items():
        course = ctx.store.courses.get(code)
        if course is None:
            problems.append(f"{code}: not in catalog")
            continue
        if code in ctx.done and code not in ctx.retakes:
            problems.append(f"{code}: already completed")
        for tree in (course.prerequisites, course.corequisites):
            if not requisite_holds(ctx, tree, t, schedule, allow_assumed=True):
                problems.append(f"{code} in {ctx.labels[t]}: requisites not met")
        units_by_term[t] += ctx.units(code)
    for t, term in enumerate(ctx.terms):
        _, cap = ctx.term_bounds(term)
        if units_by_term[t] > cap:
            problems.append(f"{term.label}: {units_by_term[t] / 2:g} course hours exceed the limit")
    for code, t in ctx.locks.items():
        if schedule.get(code) != t:
            problems.append(f"lock {code} not honored")
    return problems
