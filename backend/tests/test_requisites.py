"""Requisite parsing, using verbatim sentences from the 2026-2027 catalog."""
import pytest

from prereqpath.catalog.requisites import describe, parse_requisites


def parse(text, code="TEST 100"):
    return parse_requisites(text, code)


@pytest.mark.parametrize("text,expected", [
    ("Prerequisite, MATH 232.", "MATH 232"),
    ("Prerequisites, MATH 231 and MATH 232.", "(MATH 231 AND MATH 232)"),
    ("Prerequisite, MATH 233 or MATH 235.", "(MATH 233 OR MATH 235)"),
    # comma + conjunction binds loosest
    ("Prerequisites, MATH 233 or MATH 235, and MATH 381.", "((MATH 233 OR MATH 235) AND MATH 381)"),
    # bare numbers inherit the subject
    ("Prerequisites, MATH 381 and 383.", "(MATH 381 AND MATH 383)"),
    ("Prerequisite, MATH 521, 524, or 528.", "(MATH 521 OR MATH 524 OR MATH 528)"),
    ("Prerequisites, MATH 661, 662, 668, and 669.", "(MATH 661 AND MATH 662 AND MATH 668 AND MATH 669)"),
    # 'either' / 'one of' group an OR chain under an AND
    ("Prerequisites, MATH 383 and either MATH 577 or MATH 347.", "(MATH 383 AND (MATH 577 OR MATH 347))"),
    ("Prerequisites, COMP 116 and one of MATH 347 or MATH 577.", "(COMP 116 AND (MATH 347 OR MATH 577))"),
    # clause starting with "and"
    ("Prerequisites, MATH 233 or 235; and MATH 347, and MATH 381.", "((MATH 233 OR MATH 235) AND MATH 347 AND MATH 381)"),
    # cross-listing slash notation
    ("Prerequisites, MATH/ STOR 235 or MATH 233; and STOR 215 or STOR 315 or MATH 381 or COMP 283.",
     "((MATH 235 OR STOR 235 OR MATH 233) AND (STOR 215 OR STOR 315 OR MATH 381 OR COMP 283))"),
])
def test_structure(text, expected):
    result = parse(text)
    assert describe(result.prerequisites) == expected
    assert result.status == "parsed"


def test_substitution_with_grade():
    r = parse("Prerequisites, MATH 233 or MATH 235, and MATH 381; A grade of A- or better in STOR 215 may substitute for MATH 381.")
    assert describe(r.prerequisites) == "((MATH 233 OR MATH 235) AND (MATH 381 OR STOR 215 (≥A-)))"
    assert r.status == "parsed"


def test_grade_prefix_and_placement_alternative():
    r = parse("Prerequisite, A grade of C- or better in MATH 231 or placement by the department.", "MATH 232")
    assert describe(r.prerequisites) == "(MATH 231 (≥C-) OR PLACEMENT)"
    assert r.prerequisites.items[1].token == "PLACEMENT:MATH 232"


def test_requires_grade_clause_makes_placement_an_alternative_to_everything():
    r = parse("Prerequisites, MATH 110 and 130; Requires a grade of C- or better in MATH 130 or placement by the department.",
              "MATH 231")
    assert describe(r.prerequisites) == "((MATH 110 AND MATH 130 (≥C-)) OR PLACEMENT)"
    assert r.status == "partial"          # an interpretation was applied, so it is flagged for review


def test_grade_required_for_all_listed_courses():
    r = parse("Prerequisite, MATH 110; a grade of C- or better is required.")
    assert describe(r.prerequisites) == "MATH 110 (≥C-)"
    r = parse("Prerequisite, MATH 231 or MATH 241; a grade of C or better is required.")
    assert describe(r.prerequisites) == "(MATH 231 (≥C) OR MATH 241 (≥C))"


def test_grade_over_one_of_the_following_list():
    r = parse("Prerequisite, A C or better in one of the following courses: MATH 130, 152, 210, 231, 129P, or PHIL 155, or STOR 120, 151, 155.")
    assert r.status == "parsed"
    codes = [(i.code, i.min_grade) for i in r.prerequisites.items]
    assert ("MATH 129P", "C") in codes and ("PHIL 155", "C") in codes and ("STOR 155", "C") in codes
    assert len(codes) == 9


def test_pre_or_corequisite_may_be_concurrent():
    r = parse("Prerequisite, MATH 233 or MATH 235; Pre- or corequisite, MATH 383.")
    assert describe(r.prerequisites) == "((MATH 233 OR MATH 235) AND MATH 383 [may be concurrent])"


def test_corequisite_goes_to_corequisites():
    r = parse("Corequisite, MATH 110.")
    assert r.prerequisites is None
    assert describe(r.corequisites) == "MATH 110 [may be concurrent]"


def test_permission_for_students_lacking_prerequisite_is_an_alternative():
    r = parse("Prerequisite, MATH 383; permission of the instructor for students lacking the prerequisite.", "MATH 594")
    assert describe(r.prerequisites) == "(MATH 383 OR PERMISSION)"


def test_ambiguous_and_or_mix_is_flagged_not_silently_trusted():
    r = parse("Prerequisites, MATH 383 and MATH 347 or MATH 577.")
    assert r.status == "partial"
    assert any("needs review" in n for n in r.notes)


def test_grade_scope_ambiguity_is_flagged():
    r = parse("Prerequisite, MATH 232 or a B or better in MATH 231 or MATH 210.")
    assert r.status == "partial"


def test_uninterpretable_text_becomes_explicit_condition():
    r = parse("Prerequisite, Successful completion of the written comprehensive examination degree requirement.")
    assert r.status == "unparsed"
    assert r.prerequisites.kind == "condition" and not r.prerequisites.recognized


def test_recognized_condition_kept():
    r = parse("Prerequisites, MATH 383 and junior standing.")
    assert r.prerequisites.items[1].kind == "condition" and r.prerequisites.items[1].recognized


def test_no_requisites():
    assert parse(None).status == "none"
    assert parse("   ").status == "none"
