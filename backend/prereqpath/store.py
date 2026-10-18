"""Loads the committed catalog dataset and applies hand-verified overlays.

Verification is pinned to the exact source text it was checked against. If the
catalog text changes, the record is downgraded to "needs_reverification" (still
usable, but flagged) instead of silently keeping a stale "verified" label.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from . import DATA_DIR
from .catalog.exams import award_for
from .catalog.programs import sha256
from .catalog.requisites import normalize
from .models import (Course, CourseFilter, Program, ProgramListing, Requirement, Source,
                     Verification)


# Obvious misspellings in the catalog's exam tables, merged with their correctly
# spelled rows (the original spelling is kept in each row's source text).
EXAM_NAME_FIXES = {"Physics C Meachnics": "Physics C Mechanics"}


class CatalogStore:
    def __init__(self, catalog_year: str, data_dir: Path = DATA_DIR):
        self.catalog_year = catalog_year
        self.root = data_dir / "catalog" / catalog_year
        self.verified_root = data_dir / "verified" / catalog_year
        if not self.root.exists():
            raise FileNotFoundError(f"No catalog data for {catalog_year}")
        self.courses: dict[str, Course] = {}
        for path in sorted((self.root / "courses").glob("*.json")):
            for raw in json.loads(path.read_text(encoding="utf-8"))["courses"]:
                course = Course.model_validate(raw)
                self.courses[course.code] = course
        self._apply_course_overlay()
        self._cross_listed: dict[str, set[str]] = {}
        for course in self.courses.values():
            for other in course.same_as:
                self._cross_listed.setdefault(course.code, set()).add(other)
                self._cross_listed.setdefault(other, set()).add(course.code)
        index = self.root / "programs" / "index.json"
        self.listings: dict[str, ProgramListing] = {}
        if index.exists():
            for raw in json.loads(index.read_text(encoding="utf-8"))["programs"]:
                listing = ProgramListing.model_validate(raw)
                self.listings[listing.id] = listing
        self.exam_awards: list[dict] = []
        exam_path = self.root / "exam_credit.json"
        if exam_path.exists():
            for row in json.loads(exam_path.read_text(encoding="utf-8"))["awards"]:
                if row["exam"] in EXAM_NAME_FIXES:
                    row = {**row, "exam": EXAM_NAME_FIXES[row["exam"]],
                           "note": f"Catalog spells this exam \"{row['exam']}\"; treated as the same exam."}
                self.exam_awards.append(row)
        self.programs: dict[str, Program] = {}
        for path in sorted((self.verified_root / "programs").glob("*.json")):
            program = self._load_verified_program(json.loads(path.read_text(encoding="utf-8")))
            self.programs[program.id] = program
            if program.id in self.listings:
                self.listings[program.id].requirements_status = "verified"

    # ------------------------------------------------------------ courses
    def _apply_course_overlay(self) -> None:
        path = self.verified_root / "course_requisites.json"
        if not path.exists():
            return
        overlay = json.loads(path.read_text(encoding="utf-8"))
        by, on = overlay["verified_by"], overlay["verified_on"]
        for code, entry in overlay["courses"].items():
            course = self.courses.get(code)
            if course is None:
                continue
            if normalize(entry["raw"]) != (course.requisites_raw or ""):
                course.requisites_status = "needs_reverification"
                course.requisites_notes.append(
                    f"verified {on} against different text; catalog text has changed since review")
                continue
            if not entry.get("confirm_parse"):
                update = {"prerequisites": entry.get("prerequisites"), "corequisites": entry.get("corequisites")}
                validated = Course.model_validate({**course.model_dump(), **update})
                course.prerequisites, course.corequisites = validated.prerequisites, validated.corequisites
            course.requisites_status = "verified"
            course.requisites_notes = [f"interpretation verified {on} by {by}"] + entry.get("notes", [])

    def exam_award(self, kind: str, exam: str, score: int) -> Optional[dict]:
        return award_for(self.exam_awards, kind, exam, score)

    def exam_options(self) -> list[dict]:
        options: dict[tuple[str, str], list[int]] = {}
        for row in self.exam_awards:
            options.setdefault((row["type"], row["exam"]), []).append(row["min_score"])
        return [{"type": k, "exam": e, "min_scores": sorted(s)} for (k, e), s in sorted(options.items())]

    def course(self, code: str) -> Optional[Course]:
        return self.courses.get(self.canonical(code))

    def canonical(self, code: str) -> str:
        """Normalize spacing/case; map an honors code like 'MATH 381H' to 'MATH 381'
        when the catalog lists no separate honors course (honors sections fulfill
        the same requirements, per program-page footnotes)."""
        m = re.fullmatch(r"\s*([A-Za-z]{2,4})\s*(\d{2,3}[A-Za-z]{0,2})\s*", code or "")
        if not m:
            return (code or "").strip().upper()
        code = f"{m.group(1).upper()} {m.group(2).upper()}"
        if code not in self.courses and code.endswith("H") and code[:-1] in self.courses:
            return code[:-1]
        return code

    def equivalents(self, code: str) -> set[str]:
        """Codes that count as `code`: itself plus catalog cross-listings ("Same as")."""
        return {code} | self._cross_listed.get(code, set())

    def matching(self, flt: CourseFilter) -> list[Course]:
        out = []
        for c in self.courses.values():
            if c.subject not in flt.subjects or c.code in flt.exclude_codes:
                continue
            if any(c.number.endswith(s) for s in flt.exclude_suffixes):
                continue
            if flt.number_above is not None and not c.number_int > flt.number_above:
                continue
            if flt.number_at_least is not None and not c.number_int >= flt.number_at_least:
                continue
            if flt.number_below is not None and not c.number_int < flt.number_below:
                continue
            out.append(c)
        return sorted(out, key=lambda c: c.code)

    def search(self, query: str, limit: int = 20) -> list[Course]:
        q = query.strip().upper()
        if not q:
            return []
        compact = q.replace(" ", "")
        exact, prefix, title = [], [], []
        for c in self.courses.values():
            code = c.code.replace(" ", "")
            if code == compact:
                exact.append(c)
            elif code.startswith(compact):
                prefix.append(c)
            elif len(q) >= 3 and q in c.title.upper():
                title.append(c)
        return (exact + sorted(prefix, key=lambda c: (c.subject, c.number_int, c.number)) + title)[:limit]

    # ----------------------------------------------------------- programs
    def _load_verified_program(self, spec: dict) -> Program:
        parsed_path = self.root / "programs" / "parsed" / f"{spec['program_id']}.json"
        current_sha = None
        if parsed_path.exists():
            current_sha = json.loads(parsed_path.read_text(encoding="utf-8"))["source"].get("sha256")
        stale = current_sha is not None and current_sha != spec["verified_requirements_sha256"]
        status = "needs_reverification" if stale else "verified"
        base_notes = ["requirements-table text changed since verification"] if stale else []
        if current_sha is None:
            base_notes.append("parsed source for comparison is missing; verification could not be re-checked")

        def build(node: dict, parent_core: bool) -> Requirement:
            core = node.get("core", parent_core)
            text = node.get("source_text", "")
            return Requirement(
                id=node["id"], label=node["label"], kind=node["kind"], course=node.get("course"),
                children=[build(c, core) for c in node.get("children", [])],
                count=node.get("count"), min_hours=node.get("min_hours"), min_grade=node.get("min_grade"),
                filter=CourseFilter.model_validate(node["filter"]) if node.get("filter") else None,
                bundles=node.get("bundles", []),
                conditional_options=node.get("conditional_options", []),
                core=core,
                source=Source(url=spec["url"], catalog_year=spec["catalog_year"],
                              section=node.get("section", node["label"]), text=text, sha256=sha256(text)),
                verification=Verification(status=status, by=spec["verified_by"], on=spec["verified_on"],
                                          notes=base_notes + node.get("notes", [])))

        return Program(
            id=spec["program_id"], name=spec["name"], kind=spec["kind"], degree=spec.get("degree"),
            catalog_year=spec["catalog_year"], url=spec["url"], total_hours=spec.get("total_hours"),
            requirements=[build(n, n.get("core", True)) for n in spec["requirements"]],
            notes=spec.get("notes", []),
            exclusive_groups=spec.get("exclusive_groups", []),
            concentration_of=spec.get("concentration_of"),
            verification=Verification(status=status, by=spec["verified_by"], on=spec["verified_on"], notes=base_notes),
            source=Source(url=spec["url"], catalog_year=spec["catalog_year"], section="Requirements",
                          sha256=spec["verified_requirements_sha256"]))

    def program(self, program_id: str) -> Optional[Program]:
        return self.programs.get(program_id)


def walk(nodes: Iterable[Requirement]):
    for n in nodes:
        yield n
        yield from walk(n.children)


@lru_cache(maxsize=4)
def get_store(catalog_year: str) -> CatalogStore:
    return CatalogStore(catalog_year)


def available_catalog_years(data_dir: Path = DATA_DIR) -> list[str]:
    root = data_dir / "catalog"
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []
