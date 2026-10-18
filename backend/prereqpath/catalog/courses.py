"""Parse catalog.unc.edu/courses/<subject>/ pages (CourseLeaf `div.courseblock`)."""
from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

from ..models import Course, Source
from .requisites import normalize, parse_requisites

CODE_RE = re.compile(r"^([A-Z]{2,4})\s+(\d{2,3})([A-Z]{0,2})\.?$")  # first-year seminars use 2 digits
HOURS_RE = re.compile(r"^(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s+Credits?\.?$", re.I)


def parse_gen_ed(raw: str | None) -> list[str]:
    """Course-level IDEAs attributes. Attributes limited to designated sections
    (e.g. "FY-LAUNCH (only designated sections)") are NOT course-level and are
    left out; they remain visible in gen_ed_raw."""
    codes = []
    for piece in (raw or "").split(","):
        piece = piece.strip().rstrip(".")
        if "designated section" in piece.lower():
            continue
        piece = re.sub(r"\(.*?\)", "", piece).strip()
        if re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*", piece):
            codes.append(piece)
    return sorted(set(codes))


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\xa0", " ")).strip() if node else ""


def _field(block, cls: str) -> str | None:
    span = block.select_one(f"span.detail-{cls}")
    if span is None:
        return None
    label = span.select_one("span.label")
    if label:
        label.extract()
    value = _text(span)
    return value or None


def parse_subject_page(html: str, url: str, catalog_year: str, retrieved_at: str | None) -> tuple[list[Course], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    courses: list[Course] = []
    problems: list[str] = []
    for block in soup.select("div.courseblock"):
        code_text = _text(block.select_one(".detail-code"))
        m = CODE_RE.match(code_text.replace(" ", " "))
        if not m:
            problems.append(f"unrecognized course code {code_text!r}")
            continue
        subject, digits, suffix = m.groups()
        code = f"{subject} {digits}{suffix}"
        hours_text = _text(block.select_one(".detail-hours"))
        h = HOURS_RE.match(hours_text)
        if not h:
            problems.append(f"{code}: unrecognized credit hours {hours_text!r}")
            continue
        credits_min = float(h.group(1))
        credits_max = float(h.group(2) or h.group(1))
        requisites_raw = _field(block, "requisites")
        gen_ed_raw = _field(block, "idea_action")
        same_as_raw = _field(block, "same_as")
        parsed = parse_requisites(requisites_raw, code)
        verbatim = " | ".join(filter(None, [code_text, hours_text, requisites_raw, gen_ed_raw, same_as_raw]))
        courses.append(Course(
            code=code, subject=subject, number=digits + suffix, number_int=int(digits),
            title=_text(block.select_one(".detail-title")).rstrip("."),
            credits_min=credits_min, credits_max=credits_max,
            description=_text(block.select_one(".courseblockextra")),
            gen_ed=parse_gen_ed(gen_ed_raw),
            gen_ed_raw=gen_ed_raw,
            requisites_raw=normalize(requisites_raw) if requisites_raw else None,
            prerequisites=parsed.prerequisites, corequisites=parsed.corequisites,
            requisites_status=parsed.status, requisites_notes=parsed.notes,
            same_as=sorted({f"{a} {b}" for a, b in re.findall(r"([A-Z]{2,4})\s+(\d{3}[A-Z]{0,2})", same_as_raw or "")}),
            repeat_rules=_field(block, "repeat_rules"),
            grading_status=_field(block, "grading_status"),
            source=Source(url=url, catalog_year=catalog_year, section=code, text=verbatim,
                          retrieved_at=retrieved_at,
                          sha256=hashlib.sha256(verbatim.encode("utf-8")).hexdigest()),
        ))
    return courses, problems


def subject_pages(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    paths = {a["href"] for a in soup.select("a[href]") if re.fullmatch(r"/courses/[a-z]+/", a["href"])}
    return sorted(paths)
