"""Request/response shapes for the planner (also the public API contract)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from ..models import GRADE_POINTS

NON_LETTER_GRADES = {"P", "PS", "TR", "BE"}


class CompletedCourse(BaseModel):
    code: str
    grade: Optional[str] = None           # A..F, or P/PS/TR/BE; None = not provided
    origin: Literal["unc", "transfer", "exam"] = "unc"
    in_progress: bool = False             # currently enrolled; assumed completed before the first planning term
    credits: Optional[float] = Field(None, gt=0, le=20)   # only needed for courses not in the catalog

    @field_validator("grade")
    @classmethod
    def _grade(cls, v):
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if v not in GRADE_POINTS and v not in NON_LETTER_GRADES:
            raise ValueError(f"Unknown grade {v!r}")
        return v


class Lock(BaseModel):
    code: str
    term: str


class PlanRequest(BaseModel):
    catalog_year: str = "2026-2027"
    programs: list[str] = Field(min_length=1, max_length=3)
    entry_term: str = "Fall 2026"
    first_term: str = "Spring 2027"
    graduation_term: str = "Spring 2030"
    include_summer: bool = False
    min_credits: int = Field(12, ge=0, le=21)
    max_credits: int = Field(18, ge=1, le=21)
    summer_max_credits: int = Field(8, ge=0, le=14)
    target_program_credits: int = Field(8, ge=3, le=18)   # soft target for program coursework per semester
    completed: list[CompletedCourse] = Field(default_factory=list, max_length=150)
    tokens: list[str] = Field(default_factory=list, max_length=50)   # e.g. "PLACEMENT:MATH 231"
    locks: list[Lock] = Field(default_factory=list, max_length=30)
    exclude: list[str] = Field(default_factory=list, max_length=60)
    alternatives: int = Field(1, ge=1, le=3)
    diagnose: bool = True


class Issue(BaseModel):
    severity: Literal["info", "warning", "blocker"]
    code: str
    message: str
    source_url: Optional[str] = None
    course: Optional[str] = None
    term: Optional[str] = None


class PlannedCourse(BaseModel):
    code: str
    title: str
    credits: float
    reasons: list[str]
    requirement_ids: list[str] = Field(default_factory=list)
    contingencies: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requisites_status: str
    gen_ed: list[str] = Field(default_factory=list)
    source_url: str


class PlannedTerm(BaseModel):
    term: str
    courses: list[PlannedCourse]
    course_credits: float
    unassigned_credits: float             # Gen Ed / elective hours not yet assigned to specific courses
    total_credits: float


class RequirementStatus(BaseModel):
    id: str
    label: str
    kind: str
    status: Literal["completed", "planned", "uncertain", "unmet", "not_needed"]
    courses: list[dict] = Field(default_factory=list)   # {code, term|None, completed: bool}
    core: bool
    min_hours: Optional[int] = None
    count: Optional[int] = None
    source: dict
    verification: dict
    children: list["RequirementStatus"] = Field(default_factory=list)


class Plan(BaseModel):
    terms: list[PlannedTerm]
    requirements: dict[str, list[RequirementStatus]]    # program id -> tree
    summary: dict
    objective: Optional[float] = None


class Infeasibility(BaseModel):
    summary: str
    causes: list[str]
    suggestions: list[str]


class PlanResponse(BaseModel):
    status: Literal["feasible", "infeasible"]
    plan_status: Literal["provisional"] = "provisional"
    graduation_certified: Literal[False] = False
    certification_note: str = ("Provisional plan generated from the published catalog. It is not an official "
                               "degree audit and does not certify graduation; confirm with your advisor and Tar Heel Tracker.")
    catalog_year: str
    programs: list[dict]
    plans: list[Plan] = Field(default_factory=list)
    infeasibility: Optional[Infeasibility] = None
    issues: list[Issue] = Field(default_factory=list)
    not_modeled: list[str] = Field(default_factory=list)
    solver: dict = Field(default_factory=dict)
