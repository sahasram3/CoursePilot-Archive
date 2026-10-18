"""Catalog data model shared by the scraper, the solver, and the API.

Every course and requirement keeps where it came from (`Source`) and how much
we trust its interpretation (`Verification`). Nothing here certifies anything.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

GRADE_POINTS = {
    "A+": 12, "A": 11, "A-": 10, "B+": 9, "B": 8, "B-": 7,
    "C+": 6, "C": 5, "C-": 4, "D+": 3, "D": 2, "D-": 1, "F": 0,
}

VerificationStatus = Literal[
    "verified",             # a person checked this interpretation against the cited source text
    "parsed",               # produced by the parser from structured markup; not hand-checked
    "uncertain",            # could not be interpreted confidently; never treated as satisfied
    "needs_reverification", # was verified, but the source text has since changed
]


class Source(BaseModel):
    url: str
    catalog_year: str
    section: Optional[str] = None
    text: Optional[str] = None           # verbatim source text this record was derived from
    retrieved_at: Optional[str] = None
    sha256: Optional[str] = None         # hash of the verbatim source text (not the whole page)


class Verification(BaseModel):
    status: VerificationStatus
    by: Optional[str] = None
    on: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- requisites
class CourseReq(BaseModel):
    kind: Literal["course"] = "course"
    code: str
    min_grade: Optional[str] = None
    concurrent_ok: bool = False          # "pre- or corequisite" / corequisite: same term allowed


class AllReq(BaseModel):
    kind: Literal["all"] = "all"
    items: list["Requisite"]


class AnyReq(BaseModel):
    kind: Literal["any"] = "any"
    items: list["Requisite"]


class TokenReq(BaseModel):
    """Placement or permission: satisfied only if the student says they have it."""
    kind: Literal["placement", "permission"]
    token: str                           # e.g. "PLACEMENT:MATH 231"
    text: str


class ConditionReq(BaseModel):
    """A recognized-but-unmodeled or unparsed condition (standing, admission...)."""
    kind: Literal["condition"] = "condition"
    text: str
    recognized: bool = False


Requisite = Annotated[
    Union[CourseReq, AllReq, AnyReq, TokenReq, ConditionReq],
    Field(discriminator="kind"),
]
AllReq.model_rebuild()
AnyReq.model_rebuild()


class Course(BaseModel):
    code: str
    subject: str
    number: str                          # "383L", "691H"
    number_int: int
    title: str
    credits_min: float                   # some courses carry 0.5 / 1.5 hours
    credits_max: float
    description: str = ""
    gen_ed: list[str] = Field(default_factory=list)
    gen_ed_raw: Optional[str] = None
    requisites_raw: Optional[str] = None
    prerequisites: Optional[Requisite] = None
    corequisites: Optional[Requisite] = None
    requisites_status: Literal["none", "parsed", "partial", "unparsed", "verified", "needs_reverification"] = "none"
    requisites_notes: list[str] = Field(default_factory=list)
    same_as: list[str] = Field(default_factory=list)
    repeat_rules: Optional[str] = None
    grading_status: Optional[str] = None
    source: Source

    @property
    def variable_credit(self) -> bool:
        return self.credits_min != self.credits_max


# --------------------------------------------------------------- requirements
class CourseFilter(BaseModel):
    subjects: list[str]
    number_above: Optional[int] = None   # strictly greater than
    number_at_least: Optional[int] = None
    number_below: Optional[int] = None   # strictly less than
    exclude_codes: list[str] = Field(default_factory=list)
    exclude_suffixes: list[str] = Field(default_factory=list)  # e.g. "L" for 1-credit labs
    # Courses numbered at/above this still COUNT when completed or locked, but the
    # planner will not suggest them on its own (e.g. graduate-level 600s).
    suggest_below: Optional[int] = None


class ConditionalOption(BaseModel):
    """An alternative that only applies to some students, e.g. a substitution
    allowed for current or former majors in another program."""
    course: str
    requires_program: Optional[str] = None
    text: str


class Requirement(BaseModel):
    id: str
    label: str
    kind: Literal["all", "course", "choose", "filter", "unresolved"]
    course: Optional[str] = None                  # kind == course
    children: list["Requirement"] = Field(default_factory=list)
    count: Optional[int] = None                   # choose/filter: number of courses
    min_hours: Optional[int] = None               # choose/filter: credit hours
    min_grade: Optional[str] = None
    filter: Optional[CourseFilter] = None
    bundles: list[list[str]] = Field(default_factory=list)  # each bundle counts as ONE course
    conditional_options: list[ConditionalOption] = Field(default_factory=list)
    core: bool = True                             # major/minor core vs. additional requirement
    source: Source
    verification: Verification


Requirement.model_rebuild()


class Program(BaseModel):
    id: str
    name: str
    kind: Literal["major", "minor"]
    degree: Optional[str] = None                  # "BA", "BS", "BSBA"...
    catalog_year: str
    url: str
    total_hours: Optional[int] = None
    requirements: list[Requirement]
    notes: list[str] = Field(default_factory=list)
    # Courses a student cannot both receive credit for, e.g. [["ECON 470", "ECON 570"]].
    exclusive_groups: list[list[str]] = Field(default_factory=list)
    concentration_of: Optional[str] = None
    verification: Verification
    source: Source


class ProgramListing(BaseModel):
    """A program discovered on the official index; may not have parsed requirements yet."""
    id: str
    name: str
    kind: Literal["major", "minor"]
    degree: Optional[str] = None
    url: str
    catalog_year: str
    concentration_of: Optional[str] = None
    requirements_status: Literal["verified", "parsed", "not_parsed"] = "not_parsed"
