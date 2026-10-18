"""Academic terms. UNC runs Fall and Spring semesters plus optional summer sessions
(modeled here as a single 'Summer' planning term)."""
from __future__ import annotations

import re
from dataclasses import dataclass

SEASONS = ("Spring", "Summer", "Fall")   # calendar order within a year


@dataclass(frozen=True, order=True)
class Term:
    year: int
    season_index: int

    @property
    def season(self) -> str:
        return SEASONS[self.season_index]

    @property
    def label(self) -> str:
        return f"{self.season} {self.year}"

    @property
    def is_summer(self) -> bool:
        return self.season == "Summer"

    @classmethod
    def parse(cls, text: str) -> "Term":
        m = re.fullmatch(r"\s*(Spring|Summer|Fall)\s+(\d{4})\s*", text or "")
        if not m:
            raise ValueError(f"Term must look like 'Fall 2026', got {text!r}")
        year = int(m.group(2))
        if not 2000 <= year <= 2100:
            raise ValueError(f"Implausible year in {text!r}")
        return cls(year, SEASONS.index(m.group(1)))

    def next(self) -> "Term":
        return Term(self.year + 1, 0) if self.season_index == 2 else Term(self.year, self.season_index + 1)


def term_range(start: Term, end: Term, *, include_summer: bool) -> list[Term]:
    if end < start:
        raise ValueError("Graduation term is before the first planning term")
    out, t = [], start
    while t <= end:
        if include_summer or not t.is_summer:
            out.append(t)
        t = t.next()
    return out


def regular_semesters_between(first: Term, last: Term) -> int:
    """Fall/Spring semesters from `first` through `last` inclusive (summers excluded)."""
    return len(term_range(first, last, include_summer=False)) if last >= first else 0


def catalog_year_for_entry(entry: Term) -> str:
    """The catalog edition whose requirements apply to a student entering in `entry`."""
    start = entry.year if entry.season == "Fall" else entry.year - 1
    return f"{start}-{start + 1}"
