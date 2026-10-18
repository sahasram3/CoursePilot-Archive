"""The committed 2026-2027 dataset and the hand-verified overlays."""
import json

import pytest

from prereqpath import DATA_DIR
from prereqpath.catalog.courses import parse_gen_ed
from prereqpath.catalog.programs import discover_programs
from prereqpath.store import get_store, walk

YEAR = "2026-2027"


@pytest.fixture(scope="module")
def store():
    return get_store(YEAR)


def test_full_course_catalog_loaded(store):
    assert len(store.courses) > 10_000
    subjects = {c.subject for c in store.courses.values()}
    assert len(subjects) >= 150


def test_course_facts_match_catalog(store):
    calc2 = store.courses["MATH 232"]
    assert calc2.credits_min == calc2.credits_max == 4
    assert calc2.title.startswith("Calculus of Functions of One Variable II")
    assert "FC-QUANT" in calc2.gen_ed
    # FY-LAUNCH only applies to designated sections: never a course-level attribute
    assert "FY-LAUNCH" not in store.courses["MATH 231"].gen_ed
    assert store.courses["MATH 231"].source.url == "https://catalog.unc.edu/courses/math/"


def test_fractional_and_seminar_courses_present(store):
    assert any(c.credits_min == 1.5 for c in store.courses.values() if c.subject == "BUSI")
    assert any(c.number_int < 100 for c in store.courses.values() if c.subject == "MATH")   # first-year seminars


def test_gen_ed_parsing():
    assert parse_gen_ed("FY-LAUNCH (only designated sections), FC-QUANT.") == ["FC-QUANT"]
    assert parse_gen_ed("FC-NATSCI, FC-LAB.") == ["FC-LAB", "FC-NATSCI"]


def test_requisite_overlay_applied_and_pinned(store):
    c381 = store.courses["MATH 381"]
    assert c381.requisites_status == "verified"
    grades = {i.code: i.min_grade for i in c381.prerequisites.items}
    assert grades == {"MATH 232": None, "MATH 231": "B", "MATH 210": "B"}
    assert store.courses["MATH 564"].prerequisites.kind == "all"
    overlay = json.loads((DATA_DIR / "verified" / YEAR / "course_requisites.json").read_text(encoding="utf-8"))
    for code, entry in overlay["courses"].items():
        assert store.courses[code].requisites_status == "verified", code
        assert store.courses[code].requisites_raw == entry["raw"]


def test_math_ba_verified_and_matches_current_catalog_text(store):
    program = store.program("mathematics-major-ba")
    assert program.verification.status == "verified"
    parsed = json.loads((DATA_DIR / "catalog" / YEAR / "programs" / "parsed" / "mathematics-major-ba.json")
                        .read_text(encoding="utf-8"))
    assert parsed["source"]["sha256"] == program.source.sha256
    for node in walk(program.requirements):
        assert node.source.url == program.url
        assert node.source.catalog_year == YEAR
        assert node.verification.status == "verified"


def test_generic_parser_agrees_with_verified_math_ba(store):
    """The structure-driven parser independently finds the same named courses."""
    parsed = json.loads((DATA_DIR / "catalog" / YEAR / "programs" / "parsed" / "mathematics-major-ba.json")
                        .read_text(encoding="utf-8"))

    def codes(nodes):
        out = set()
        for n in nodes:
            if n.get("course"):
                out.add(n["course"])
            out |= codes(n.get("children", []))
        return out
    verified = {n.course for n in walk(store.program("mathematics-major-ba").requirements) if n.course}
    assert codes(parsed["requirements"]) == verified
    assert parsed["total_hours"] == 33


def test_program_discovery_covers_every_undergraduate_program(store):
    listings = store.listings
    assert len(listings) == 202
    for slug in ("environmental-science-bs", "human-development-family-studies-baed", "human-org-leadership-ba"):
        assert slug in listings and listings[slug].kind == "major"     # slugs without "major"
    assert "pharmd" not in listings and "doctor-of-dental-surgery-dds" not in listings
    tracks = [p for p in listings.values() if p.concentration_of]
    assert tracks and all(p.concentration_of in listings for p in tracks)
    assert listings["biology-major-bs-quantitative-biology-track"].concentration_of == "biology-major-bs"


def test_discovery_on_minimal_html():
    html = ('<a href="/undergraduate/programs-study/x-major-ba/">X Major, B.A.</a>'
            '<a href="/undergraduate/programs-study/x-minor/">X Minor</a>'
            '<a href="/undergraduate/programs-study/pharmd/">PharmD</a>'
            '<a href="/archives/2020/whatever/">old</a>')
    listings, skipped = discover_programs(html, YEAR)
    assert [(p.id, p.kind, p.degree) for p in listings] == [("x-major-ba", "major", "BA"), ("x-minor", "minor", None)]
    assert skipped == ["pharmd"]
