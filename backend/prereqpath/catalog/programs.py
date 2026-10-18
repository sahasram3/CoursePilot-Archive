"""Program discovery and generic requirement-table parsing (CourseLeaf markup).

`sc_courselist` rows carry structure in their CSS classes:
  areaheader -> group heading, orclass -> alternative to the previous row,
  listsum -> total hours, codecol "A & B" -> courses taken together,
  comment rows ("At least two of:", "Either:") -> choice groups over following rows.
The generic parser marks its output "parsed" (or "uncertain" for free-text rows);
only a hand-verified overlay (data/verified/...) can mark a program "verified".
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from bs4 import BeautifulSoup

from ..models import (CourseFilter, Program, ProgramListing, Requirement, Source,
                      Verification)

BASE = "https://catalog.unc.edu"
PROGRAM_PATH_RE = re.compile(r"^/undergraduate/programs-study/([a-z0-9-]+)/$")
NON_UNDERGRADUATE = ("doctor-of-dental-surgery-dds", "pharmd")
DEGREE_SUFFIX_RE = re.compile(r"-(ba|bs|bsba|baed|bsn|bsph|bmus|bfa|bme|ab|bsed|bas)(?:-|$)")
COURSE_RE = re.compile(r"\b([A-Z]{2,4})\s+(\d{2,3}[A-Z]{0,2})\b")
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\xa0", " ")).strip() if node else ""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------- discovery
def discover_programs(index_html: str, catalog_year: str) -> tuple[list[ProgramListing], list[str]]:
    """Every program linked from the official index, including slugs that do not
    contain 'major' (e.g. environmental-science-bs). Professional doctorates are
    linked from the index but are not undergraduate programs."""
    soup = BeautifulSoup(index_html, "html.parser")
    found: dict[str, ProgramListing] = {}
    skipped: list[str] = []
    for a in soup.select("a[href]"):
        m = PROGRAM_PATH_RE.match(a["href"])
        name = _text(a)
        if not m or not name:
            continue
        slug = m.group(1)
        if slug in NON_UNDERGRADUATE:
            skipped.append(slug)
            continue
        if slug in found:
            continue
        degree = DEGREE_SUFFIX_RE.search(slug)
        found[slug] = ProgramListing(
            id=slug, name=name, kind="minor" if "minor" in slug.split("-") else "major",
            degree=degree.group(1).upper() if degree else None,
            url=f"{BASE}/undergraduate/programs-study/{slug}/", catalog_year=catalog_year)
    listings = sorted(found.values(), key=lambda p: p.name)
    _link_concentrations(listings)
    return listings, sorted(set(skipped))


def _link_concentrations(listings: list[ProgramListing]) -> None:
    by_name = {p.name: p for p in listings}
    for p in listings:
        if not re.search(r"(Concentration|Track|Option)$", p.name):
            continue
        base_name = re.split(r"\s*[–—-]\s*(?=[A-Z][^,]*(?:Concentration|Track|Option)$)", p.name)[0].strip()
        base = by_name.get(base_name)
        if base is None:  # fall back to slug prefix: biology-major-bs-quantitative-biology-track
            base = next((b for b in listings if b is not p and p.id.startswith(b.id + "-")), None)
        if base is not None and base is not p:
            p.concentration_of = base.id


# -------------------------------------------------------------- page parsing
def requirement_tables(soup: BeautifulSoup):
    """The program's requirement list(s), excluding advisory course lists that
    some pages place in the same tab (e.g. Math's 'recommended for graduate study')."""
    container = soup.select_one("#requirementstextcontainer") or soup
    tables = container.select("table.sc_courselist")
    main = [t for i, t in enumerate(tables)
            if i == 0 or t.select_one("tr.areaheader") or t.select_one("tr.listsum")]
    advisory = [t for t in tables if t not in main]
    return main, advisory


def requirements_text(html: str) -> str:
    """Normalized verbatim text of the requirement tables + footnotes. Its hash is
    what a hand verification is pinned to (whole-page hashes change too often)."""
    soup = BeautifulSoup(html, "html.parser")
    main, _ = requirement_tables(soup)
    container = soup.select_one("#requirementstextcontainer") or soup
    parts = [_text(t) for t in main]
    parts += [_text(f) for f in container.select("dl.sc_footnotes, .sc_footnotes")]
    return " || ".join(parts)


def _row_cells(tr):
    code = tr.select_one("td.codecol")
    hours = tr.select_one("td.hourscol")
    tds = tr.find_all("td")
    title = next((td for td in tds if td is not code and td is not hours), None)
    return _text(code), _text(title), _text(hours)


def _codes(text: str) -> list[str]:
    return [f"{a} {b}" for a, b in COURSE_RE.findall(text)]


def _int(text: str) -> Optional[int]:
    m = re.match(r"^\d+$", text.strip())
    return int(text) if m else None


def parse_program_page(html: str, listing: ProgramListing, retrieved_at: Optional[str]) -> Program:
    soup = BeautifulSoup(html, "html.parser")
    main, advisory = requirement_tables(soup)
    req_text = requirements_text(html)

    def source(section: str, text: str) -> Source:
        return Source(url=listing.url, catalog_year=listing.catalog_year, section=section, text=text,
                      retrieved_at=retrieved_at, sha256=sha256(text))

    sections: list[Requirement] = []
    total_hours = None
    counter = 0

    def new_id(prefix: str) -> str:
        nonlocal counter
        counter += 1
        return f"{prefix}{counter}"

    for t_index, table in enumerate(main):
        current = Requirement(id=new_id("section"), label="Requirements", kind="all",
                              source=source("Requirements", ""), verification=Verification(status="parsed"))
        sections.append(current)
        pending_choice: Optional[Requirement] = None
        for tr in table.select("tr"):
            classes = tr.get("class", [])
            if "hidden" in classes:
                continue
            code_text, title, hours = _row_cells(tr)
            row_text = " | ".join(x for x in (code_text, title, hours) if x)
            if "listsum" in classes:
                total_hours = _int(hours) or total_hours
                continue
            if "areaheader" in classes:
                current = Requirement(id=new_id("section"), label=title or code_text, kind="all",
                                      source=source(title or code_text, row_text),
                                      verification=Verification(status="parsed"))
                sections.append(current)
                pending_choice = None
                continue
            if "orclass" in classes or code_text.lower().startswith("or "):
                alt_codes = _codes(code_text)
                target = current.children[-1] if current.children else None
                if target is None or not alt_codes:
                    current.children.append(_uncertain(new_id("row"), row_text, source("row", row_text)))
                    continue
                if target.kind == "course":
                    target = Requirement(id=target.id, label=f"One of {target.course}", kind="choose", count=1,
                                         children=[target], core=target.core,
                                         source=target.source, verification=Verification(status="parsed"))
                    current.children[-1] = target
                if target.kind == "choose":
                    target.children.append(_course_node(new_id("row"), alt_codes, row_text, source("row", row_text)))
                    target.label = "One of " + ", ".join(c.course or c.label for c in target.children)
                    target.source.text = (target.source.text or "") + " || " + row_text
                    target.source.sha256 = sha256(target.source.text)
                continue
            if code_text:
                node = _course_node(new_id("row"), _codes(code_text), row_text, source("row", row_text))
                if pending_choice is not None and not hours:
                    pending_choice.children.append(node)
                else:
                    pending_choice = None
                    current.children.append(node)
                continue
            # Free-text row: a choice header ("At least two of:") or a rule.
            m = re.match(r"^(?:at least |choose |select )?(one|two|three|four|five|six|\d+)(?: course(?:s)?)?(?: from| of)?(?: the following)?:$",
                         title, re.I)
            if m or re.match(r"^(either|or):?$", title, re.I):
                count = 1 if not m else (NUMBER_WORDS.get(m.group(1).lower()) or int(m.group(1)))
                pending_choice = Requirement(id=new_id("choice"), label=title, kind="choose", count=count,
                                             min_hours=_int(hours), source=source("row", row_text),
                                             verification=Verification(status="parsed"))
                current.children.append(pending_choice)
                continue
            pending_choice = None
            current.children.append(_filter_or_uncertain(new_id("row"), title, hours, source("row", row_text)))

    sections = [s for s in sections if s.children]
    notes = []
    if advisory:
        notes.append(f"{len(advisory)} additional course list(s) on the requirements tab were treated as advisory, not requirements")
    any_uncertain = _has_uncertain(sections)
    return Program(
        id=listing.id, name=listing.name, kind=listing.kind, degree=listing.degree,
        catalog_year=listing.catalog_year, url=listing.url, total_hours=total_hours,
        requirements=sections, notes=notes, concentration_of=listing.concentration_of,
        verification=Verification(status="uncertain" if any_uncertain else "parsed"),
        source=source("Requirements", req_text))


def _course_node(node_id: str, codes: list[str], row_text: str, src: Source) -> Requirement:
    if not codes:
        return _uncertain(node_id, row_text, src)
    if len(codes) == 1:
        return Requirement(id=node_id, label=codes[0], kind="course", course=codes[0], source=src,
                           verification=Verification(status="parsed"))
    if "&" in row_text:   # "BIOL 101 & 101L": taken together, both required
        expanded = _expand_bare_numbers(row_text.split("|")[0])
        return Requirement(id=node_id, label=" & ".join(expanded), kind="all", source=src,
                           children=[Requirement(id=f"{node_id}.{i}", label=c, kind="course", course=c, source=src,
                                                 verification=Verification(status="parsed"))
                                     for i, c in enumerate(expanded)],
                           verification=Verification(status="parsed"))
    # "MATH 535/STOR 435": cross-listed, either code
    return Requirement(id=node_id, label=" / ".join(codes), kind="choose", count=1, source=src,
                       children=[Requirement(id=f"{node_id}.{i}", label=c, kind="course", course=c, source=src,
                                             verification=Verification(status="parsed"))
                                 for i, c in enumerate(codes)],
                       verification=Verification(status="parsed", notes=["cross-listed course"]))


def _expand_bare_numbers(text: str) -> list[str]:
    out, subject = [], None
    for m in re.finditer(r"([A-Z]{2,4})?\s*(\d{2,3}[A-Z]{0,2})\b", text):
        subject = m.group(1) or subject
        if subject:
            out.append(f"{subject} {m.group(2)}")
    return out


FILTER_RE = re.compile(
    r"^(?:at least\s+)?(?P<n>one|two|three|four|five|six|\d+)\s+(?:more\s+|additional\s+)?(?P<subj>[A-Z]{2,4})\s+courses?\s+numbered\s+(?:above|higher than)\s+(?P<num>\d{3})",
    re.I)


def _filter_or_uncertain(node_id: str, title: str, hours: str, src: Source) -> Requirement:
    m = FILTER_RE.match(title)
    if m:
        n = NUMBER_WORDS.get(m.group("n").lower()) or int(m.group("n"))
        return Requirement(id=node_id, label=title, kind="filter", count=n, min_hours=_int(hours),
                           filter=CourseFilter(subjects=[m.group("subj").upper()], number_above=int(m.group("num"))),
                           source=src, verification=Verification(
                               status="uncertain",
                               notes=["pattern-matched course filter; footnotes and exclusions not applied"]))
    return _uncertain(node_id, title, src)


def _uncertain(node_id: str, text: str, src: Source) -> Requirement:
    return Requirement(id=node_id, label=text, kind="unresolved", source=src,
                       verification=Verification(status="uncertain", notes=["free-text requirement not interpreted"]))


def _has_uncertain(nodes: list[Requirement]) -> bool:
    return any(n.verification.status == "uncertain" or _has_uncertain(n.children) for n in nodes)
