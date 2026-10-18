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
    code: str = Field(max_length=20)
    term: str = Field(max_length=20)


class ExamScore(BaseModel):
    """An AP or IB exam result, resolved through the catalog's credit table."""
    type: Literal["AP", "IB"]
    exam: str = Field(max_length=120)
    score: int = Field(ge=1, le=7)


class OtherCredit(BaseModel):
    """Credit hours that do not map to a specific UNC course (e.g. transfer electives)."""
    label: str = Field("Transfer credit", max_length=80)
    hours: float = Field(gt=0, le=90)
    origin: Literal["transfer", "exam"] = "transfer"


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
    target_program_credits: int = Field(8, ge=3, le=18)   # soft cap on program coursework per semester
    completed: list[CompletedCourse] = Field(default_factory=list, max_length=150)
    exams: list[ExamScore] = Field(default_factory=list, max_length=40)
    other_credit: list[OtherCredit] = Field(default_factory=list, max_length=20)
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
    requisites_raw: Optional[str] = None
    prerequisites_text: str = "none"
    satisfied_by: list[str] = Field(default_factory=list)   # courses/tokens that meet its requisites in this plan
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
    actions: list[dict] = Field(default_factory=list)   # {label, changes}: request edits that were re-solved as feasible


class PlanResponse(BaseModel):
    status: Literal["feasible", "infeasible"]
    plan_status: Literal["provisional"] = "provisional"
    graduation_certified: Literal[False] = False
    certification_note: str = ("Provisional plan generated from the published catalog. It is not an official "
                               "degree audit and does not certify graduation; confirm with your advisor and Tar Heel Tracker.")
    catalog_year: str
    programs: list[dict]
    completed_courses: list[dict] = Field(default_factory=list)   # normalized credit the plan starts from
    plans: list[Plan] = Field(default_factory=list)
    infeasibility: Optional[Infeasibility] = None
    issues: list[Issue] = Field(default_factory=list)
    not_modeled: list[str] = Field(default_factory=list)
    solver: dict = Field(default_factory=dict)
