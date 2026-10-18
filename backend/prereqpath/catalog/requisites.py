"""Parse UNC catalog "Requisites:" text into AND/OR requisite trees.

Conventions observed in the 2026-2027 catalog:
  "Prerequisites, MATH 233 or MATH 235, and MATH 381"  -> comma+conjunction binds loosest
  "MATH 232 or MATH 231 and MATH 210 or ..."           -> AND binds tighter than OR
  "MATH 381 and 383"                                   -> bare number inherits subject
  "MATH 383 and either MATH 577 or MATH 347"           -> 'either' groups the OR chain
  "a B or better in MATH 231"                          -> grade applies to the next course
  "; A grade of A- or better in STOR 215 may substitute for MATH 381"
  "; Pre- or corequisite, MATH 383"                    -> may be taken in the same term
  "...; permission of the instructor for students lacking the prerequisites"

Anything not understood becomes a ConditionReq(recognized=False) so it is never
silently treated as satisfied, and the course is marked "partial"/"unparsed".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..models import AllReq, AnyReq, ConditionReq, CourseReq, Requisite, TokenReq

GRADE = r"[A-D][+-]?"
COURSE_RE = re.compile(r"([A-Z]{2,4})\s+(\d{2,3}[A-Z]{0,2})\b")
BARE_NUMBER_RE = re.compile(r"(\d{3}[A-Z]{0,2})\b")

# Recognized conditions we do not model yet (kept, flagged, never assumed met in an OR).
KNOWN_CONDITIONS = [
    r"(?:first-year|sophomore|junior|senior|graduate)(?:\s*(?:,|or|and)\s*(?:first-year|sophomore|junior|senior|graduate))*\s+standing(?: or higher)?",
    r"admission to [^,;]+",
    r"(?:open|restricted|limited) to [^,;]+",
    r"(?:declared\s+)?majors? (?:only|in [^,;]+)",
    r"enrollment in [^,;]+",
    r"concurrent enrollment in [^,;]+",
]
PERMISSION_RE = re.compile(
    r"(?:(?:the\s+)?(?:permission|consent|approval) of (?:the\s+)?(?:instructor|department|school|program|director|chair|dean)(?: of [A-Za-z ]+?)?"
    r"|instructor (?:permission|consent)|departmental permission)", re.I)
PLACEMENT_RE = re.compile(r"(?:placement (?:by|from) the department|departmental placement|placement (?:exam|test)(?: score)?|placement)", re.I)


class _ParseError(Exception):
    pass


@dataclass
class ParsedRequisites:
    prerequisites: Optional[Requisite]
    corequisites: Optional[Requisite]
    status: str
    notes: list[str] = field(default_factory=list)


def normalize(text: str) -> str:
    text = text.replace("\xa0", " ").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    text = re.sub(r"^Requisites:\s*", "", text, flags=re.I)
    return text


def _expand_cross_listings(text: str) -> str:
    # "MATH/ STOR 235" is one cross-listed course offered under either code.
    return re.sub(r"\b([A-Z]{2,4})\s*/\s*([A-Z]{2,4})\s+(\d{3}[A-Z]{0,2})\b", r"(\1 \3 or \2 \3)", text)


# ------------------------------------------------------------------ tokenizer
@dataclass
class Tok:
    kind: str           # COURSE GRADE AND OR COMMA EITHER LP RP PLACEMENT PERMISSION COND
    value: str = ""


def _tokenize(body: str) -> list[Tok]:
    toks: list[Tok] = []
    i, subject = 0, None
    s = body
    while i < len(s):
        rest = s[i:]
        m = re.match(r"[\s.]+", rest)
        if m:
            i += m.end(); continue
        m = re.match(
            rf"(?:an?\s+)?(?:(?:minimum\s+)?grade\s+of\s+)?(?:an?\s+)?({GRADE})\s+or\s+(?:better|higher|above)\s+(?:in|on)\s+",
            rest, re.I)
        if m and re.match(GRADE, m.group(1)):
            toks.append(Tok("GRADE", m.group(1).upper())); i += m.end(); continue
        m = re.match(rf"(?:a\s+)?minimum\s+grade\s+of\s+({GRADE})\s+in\s+", rest, re.I)
        if m:
            toks.append(Tok("GRADE", m.group(1).upper())); i += m.end(); continue
        m = re.match(rf"\(?\s*(?:with\s+)?(?:a\s+)?(?:minimum\s+)?grade\s+of\s+({GRADE})(?:\s+or\s+(?:better|higher))?\s*\)?", rest, re.I)
        if m and toks and toks[-1].kind == "COURSE":
            toks.append(Tok("POSTGRADE", m.group(1).upper())); i += m.end(); continue
        m = COURSE_RE.match(rest)
        if m:
            subject = m.group(1)
            toks.append(Tok("COURSE", f"{m.group(1)} {m.group(2)}")); i += m.end(); continue
        m = BARE_NUMBER_RE.match(rest)
        if m and subject:
            toks.append(Tok("COURSE", f"{subject} {m.group(1)}")); i += m.end(); continue
        m = re.match(r"and/or\b", rest, re.I)
        if m:
            toks.append(Tok("OR")); i += m.end(); continue
        m = re.match(r"(?:at\s+least\s+|any\s+)?one\s+of(?:\s+the\s+following)?(?:\s+courses)?:?\s+|any\s+of\s+", rest, re.I)
        if m:
            toks.append(Tok("EITHER")); i += m.end(); continue
        m = re.match(r"(and|or|either|both)\b", rest, re.I)
        if m:
            word = m.group(1).lower()
            if word != "both":
                toks.append(Tok({"and": "AND", "or": "OR", "either": "EITHER"}[word]))
            i += m.end(); continue
        if rest[0] == ",":
            toks.append(Tok("COMMA")); i += 1; continue
        if rest[0] == "(":
            toks.append(Tok("LP")); i += 1; continue
        if rest[0] == ")":
            toks.append(Tok("RP")); i += 1; continue
        m = PERMISSION_RE.match(rest)
        if m:
            toks.append(Tok("PERMISSION", m.group(0))); i += m.end(); continue
        m = PLACEMENT_RE.match(rest)
        if m:
            toks.append(Tok("PLACEMENT", m.group(0))); i += m.end(); continue
        for pattern in KNOWN_CONDITIONS:
            m = re.match(pattern, rest, re.I)
            if m:
                toks.append(Tok("COND", m.group(0).strip())); i += m.end(); break
        else:
            raise _ParseError(f"unrecognized text: {rest[:60]!r}")
    return toks


# --------------------------------------------------------------------- parser
class _Parser:
    def __init__(self, toks: list[Tok], course_code: str, concurrent_ok: bool):
        self.toks, self.pos = toks, 0
        self.course_code = course_code
        self.concurrent_ok = concurrent_ok
        self.notes: list[str] = []

    def peek(self) -> Optional[Tok]:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def take(self, kind: str) -> Tok:
        tok = self.peek()
        if tok is None or tok.kind != kind:
            raise _ParseError(f"expected {kind}, found {tok.kind if tok else 'end'}")
        self.pos += 1
        return tok

    def parse(self) -> Requisite:
        node = self.comma_list()
        if self.peek() is not None:
            raise _ParseError(f"trailing tokens at {self.peek().kind}")
        return node

    def comma_list(self) -> Requisite:
        groups = [self.or_expr()]
        joiners: list[Optional[str]] = []
        while self.peek() and self.peek().kind == "COMMA":
            self.pos += 1
            joiner = None
            if self.peek() and self.peek().kind in ("AND", "OR"):
                joiner = self.take(self.peek().kind).kind
            joiners.append(joiner)
            groups.append(self.or_expr())
        if len(groups) == 1:
            return groups[0]
        explicit = {j for j in joiners if j}
        if len(explicit) > 1:
            raise _ParseError("mixed ', and' / ', or' list")
        if not explicit:
            self.notes.append("comma-separated list without a conjunction was read as AND")
        kind = "any" if explicit == {"OR"} else "all"
        return _combine(kind, groups)

    def or_expr(self) -> Requisite:
        first, mixed = self.and_expr()
        items = [first]
        while self.peek() and self.peek().kind == "OR":
            self.pos += 1
            item, has_and = self.and_expr()
            mixed = mixed or has_and
            items.append(item)
        if len(items) > 1 and mixed:
            # "A and B or C" is genuinely ambiguous in English; we read AND as
            # binding tighter (which matches e.g. MATH 347), but flag it.
            self.notes.append("unpunctuated mix of 'and'/'or' read with AND binding tighter; needs review")
        return _combine("any", items)

    def and_expr(self) -> tuple[Requisite, bool]:
        items = [self.unary()]
        while self.peek() and self.peek().kind == "AND":
            self.pos += 1
            items.append(self.unary())
        return _combine("all", items), len(items) > 1

    def unary(self) -> Requisite:
        tok = self.peek()
        if tok is None:
            raise _ParseError("unexpected end")
        if tok.kind == "EITHER":
            # "either A or B", "one of the following: A, B, or C" - a disjunction that
            # may use commas; it ends at ", and" or anything that is not a list item.
            self.pos += 1
            items = [self.unary()]
            while self.peek():
                kind = self.peek().kind
                if kind == "OR":
                    self.pos += 1
                elif kind == "COMMA" and self.pos + 1 < len(self.toks) and self.toks[self.pos + 1].kind != "AND":
                    self.pos += 1
                    if self.peek() and self.peek().kind == "OR":
                        self.pos += 1
                else:
                    break
                items.append(self.unary())
            return _combine("any", items)
        if tok.kind == "LP":
            self.pos += 1
            node = self.comma_list()
            self.take("RP")
            return node
        if tok.kind == "GRADE":
            self.pos += 1
            nxt = self.peek()
            if nxt is not None and nxt.kind == "EITHER":
                # "a C or better in one of the following courses: ..." -> grade on every option
                group = self.unary()
                return _map_courses(group, lambda n: n.model_copy(update={"min_grade": tok.value}))
            if nxt is None or nxt.kind != "COURSE":
                raise _ParseError("grade not followed by a course")
            node = self.atom()
            node.min_grade = tok.value
            after = self.peek()
            if after and after.kind in ("AND", "OR") and self.pos + 1 < len(self.toks) \
                    and self.toks[self.pos + 1].kind == "COURSE":
                self.notes.append(f"grade {tok.value} read as applying only to {node.code}")
            return node
        return self.atom()

    def atom(self) -> Requisite:
        tok = self.peek()
        self.pos += 1
        if tok.kind == "COURSE":
            node = CourseReq(code=tok.value, concurrent_ok=self.concurrent_ok)
            if self.peek() and self.peek().kind == "POSTGRADE":
                node.min_grade = self.take("POSTGRADE").value
            return node
        if tok.kind == "PLACEMENT":
            return TokenReq(kind="placement", token=f"PLACEMENT:{self.course_code}", text=tok.value)
        if tok.kind == "PERMISSION":
            return TokenReq(kind="permission", token=f"PERMISSION:{self.course_code}", text=tok.value)
        if tok.kind == "COND":
            return ConditionReq(text=tok.value, recognized=True)
        raise _ParseError(f"unexpected {tok.kind}")


def _combine(kind: str, items: list[Requisite]) -> Requisite:
    flat: list[Requisite] = []
    for item in items:
        if item.kind == kind:
            flat.extend(item.items)
        else:
            flat.append(item)
    if len(flat) == 1:
        return flat[0]
    return AllReq(items=flat) if kind == "all" else AnyReq(items=flat)


def _parse_body(body: str, course_code: str, concurrent_ok: bool, notes: list[str]) -> Requisite:
    toks = _tokenize(body)
    # "MATH 152, 231, STOR 112, or 113 with a grade of C- or better": a grade phrase
    # that ENDS the clause covers every course listed in it. Mid-clause ("ECON 410
    # with a grade of C or better, or COMP 550") it covers only the preceding course.
    trailing = None
    if len(toks) > 2 and toks[-1].kind == "POSTGRADE" and sum(t.kind == "COURSE" for t in toks) > 1:
        trailing = toks.pop().value
    parser = _Parser(toks, course_code, concurrent_ok)
    node = parser.parse()
    notes.extend(parser.notes)
    if trailing:
        node = _map_courses(node, lambda n: n.model_copy(update={"min_grade": n.min_grade or trailing}))
    return node


def _map_courses(node: Requisite, fn) -> Requisite:
    if node.kind == "course":
        return fn(node)
    if node.kind in ("all", "any"):
        return _combine(node.kind, [_map_courses(i, fn) for i in node.items])
    return node


# ------------------------------------------------------------------ top level
CLAUSE_SPLIT = re.compile(r";|\.\s+(?=[A-Z])")
LABEL_RE = re.compile(
    r"^(?P<label>pre-?\s*or\s*co-?requisites?|prerequisites?\s+or\s+corequisites?|co-?requisites?|pre-?requisites?)\s*[,:]?\s*(?P<body>.*)$",
    re.I)
SUBSTITUTE_RE = re.compile(
    rf"^(?:(?:an?\s+)?(?:(?:minimum\s+)?grade\s+of\s+)?(?:an?\s+)?(?P<grade>{GRADE})\s+or\s+(?:better|higher)\s+in\s+)?"
    rf"(?P<sub>[A-Z]{{2,4}}\s+\d{{3}}[A-Z]{{0,2}})\s+(?:may|can)\s+(?:be\s+)?substitute[d]?\s+for\s+(?P<orig>[A-Z]{{2,4}}\s+\d{{3}}[A-Z]{{0,2}})\.?$",
    re.I)
REQUIRES_GRADE_RE = re.compile(r"^requires?\s+(?P<body>(?:an?\s+)?(?:minimum\s+)?grade\s+of\s+.*)$", re.I)
GRADE_FOR_ALL_RE = re.compile(
    rf"^(?:(?:both|all|each)\s+)?(?:with\s+)?(?:an?\s+)?(?:minimum\s+)?grade\s+(?:of\s+)?(?P<grade>{GRADE})(?:\s+or\s+(?:better|higher))?"
    rf"(?:\s+(?:is\s+)?required)?(?:\s+in\s+(?:all|each|both|the|these)(?:\s+(?:of\s+the\s+)?(?:prerequisite|prerequisites|courses?|prerequisite courses))?)?$",
    re.I)
# "a grade of C or better in ECON 400 and 410 is required" (possibly several, joined by
# "and a grade of ..."): minimum grades for the listed courses only.
GRADE_LIST_RE = re.compile(
    rf"^(?:an?\s+)?(?:minimum\s+)?grade\s+of\s+(?P<grade>{GRADE})\s+or\s+(?:better|higher)\s+(?:is\s+required\s+)?in\s+"
    rf"(?P<list>.+?)(?:\s+(?:is|are)\s+required)?$", re.I)


def _listed_codes(text: str) -> Optional[list[str]]:
    """Course codes in "ECON 400, 410 and 470" / "ECON 470 or ECON 450"; None if anything else appears."""
    codes, subject = [], None
    for piece in re.split(r"\s*(?:,|\band\b|\bor\b)\s*", text.strip()):
        if not piece:
            continue
        m = re.fullmatch(r"(?:([A-Z]{2,4})\s+)?(\d{2,3}[A-Z]{0,2})", piece)
        if not m or not (m.group(1) or subject):
            return None
        subject = m.group(1) or subject
        codes.append(f"{subject} {m.group(2)}")
    return codes or None
LACKING_RE = re.compile(r"permission of the (?:instructor|department)[^.;]*lacking the (?:pre|co)?requisites?", re.I)


def parse_requisites(raw: Optional[str], course_code: str) -> ParsedRequisites:
    if not raw or not normalize(raw):
        return ParsedRequisites(None, None, "none")
    text = _expand_cross_listings(normalize(raw))
    notes: list[str] = []
    pre: list[Requisite] = []
    co: list[Requisite] = []
    modifiers: list[tuple[str, object]] = []
    unknown = 0
    clauses = [c.strip(" .") for c in CLAUSE_SPLIT.split(text) if c.strip(" .")]
    last_target = pre
    for clause in clauses:
        try:
            label = LABEL_RE.match(clause)
            if label:
                name = label.group("label").lower().replace(" ", "")
                body = label.group("body")
                if name.startswith("pre-orco") or name.startswith("preorco") or "orcorequisite" in name:
                    pre.append(_parse_body(body, course_code, True, notes)); last_target = pre
                elif name.startswith("co"):
                    co.append(_parse_body(body, course_code, True, notes)); last_target = co
                else:
                    pre.append(_parse_body(body, course_code, False, notes)); last_target = pre
                continue
            sub = SUBSTITUTE_RE.match(clause)
            if sub:
                modifiers.append(("substitute", (sub.group("orig").upper(),
                                                 CourseReq(code=re.sub(r"\s+", " ", sub.group("sub").upper()),
                                                           min_grade=(sub.group("grade") or None) and sub.group("grade").upper()))))
                continue
            all_grade = GRADE_FOR_ALL_RE.match(clause)
            if all_grade:
                modifiers.append(("grade_all", all_grade.group("grade").upper()))
                continue
            listed = {}
            for part in re.split(r"\s+and\s+(?=an?\s+(?:minimum\s+)?grade\s+of)", clause, flags=re.I):
                m = GRADE_LIST_RE.match(part.strip())
                codes = _listed_codes(m.group("list")) if m else None
                if not codes:
                    listed = {}
                    break
                listed.update({code: m.group("grade").upper() for code in codes})
            if listed:
                modifiers.append(("grade_list", listed))
                continue
            lead_and = re.match(r"^and\s+(.*)$", clause, re.I)
            if lead_and:
                last_target.append(_parse_body(lead_and.group(1), course_code, last_target is co, notes))
                continue
            if LACKING_RE.search(clause):
                modifiers.append(("or_token", TokenReq(kind="permission", token=f"PERMISSION:{course_code}",
                                                       text=clause)))
                continue
            req = REQUIRES_GRADE_RE.match(clause)
            if req:
                modifiers.append(("requires", _parse_body(req.group("body"), course_code, False, notes)))
                notes.append("'requires a grade' clause applied to matching courses; placement/permission in it is an alternative to the whole requirement")
                continue
            lead_or = re.match(r"^or\s+(.*)$", clause, re.I)
            body = lead_or.group(1) if lead_or else clause
            node = _parse_body(body, course_code, False, notes)
            if node.kind in ("placement", "permission") or (lead_or and last_target):
                modifiers.append(("or_token", node))
            else:
                last_target.append(node)
        except _ParseError as exc:
            unknown += 1
            last_target.append(ConditionReq(text=clause, recognized=False))
            notes.append(f"could not interpret: {clause!r} ({exc})")

    prereq = _combine("all", pre) if pre else None
    coreq = _combine("all", co) if co else None
    for kind, payload in modifiers:
        if kind == "substitute":
            orig, alt = payload
            found = False

            def swap(node, orig=orig, alt=alt):
                nonlocal found
                if node.code == orig:
                    found = True
                    return AnyReq(items=[node, alt])
                return node
            if prereq is not None:
                prereq = _map_courses(prereq, swap)
            if not found:
                notes.append(f"substitution for {orig} did not match a listed prerequisite")
                unknown += 1
        elif kind == "requires":
            grades = {}
            tokens = []
            extra = []
            for item in (payload.items if payload.kind in ("all", "any") else [payload]):
                if item.kind == "course" and item.min_grade:
                    grades[item.code] = item.min_grade
                elif item.kind in ("placement", "permission"):
                    tokens.append(item)
                else:
                    extra.append(item)
            if prereq is not None and grades:
                prereq = _map_courses(prereq, lambda n: n.model_copy(update={"min_grade": grades.get(n.code, n.min_grade)}))
            missing = set(grades) - _course_codes(prereq)
            if missing or extra:
                extra += [CourseReq(code=c, min_grade=g) for c, g in grades.items() if c in missing]
                prereq = _combine("all", ([prereq] if prereq else []) + extra)
            if tokens:
                prereq = _combine("any", ([prereq] if prereq else []) + tokens)
        elif kind == "grade_list":
            present = _course_codes(prereq)
            missing = set(payload) - present
            if missing:
                notes.append(f"grade requirement names {', '.join(sorted(missing))}, which is not among the listed prerequisites")
                unknown += 1
            if prereq is not None:
                prereq = _map_courses(prereq, lambda n, g=payload: n.model_copy(update={"min_grade": g.get(n.code, n.min_grade)}))
        elif kind == "grade_all":
            if prereq is None:
                notes.append("grade requirement with no listed prerequisite courses")
                unknown += 1
            else:
                prereq = _map_courses(prereq, lambda n, g=payload: n.model_copy(update={"min_grade": n.min_grade or g}))
        elif kind == "or_token":
            prereq = _combine("any", ([prereq] if prereq else []) + [payload]) if prereq else payload

    if unknown and (prereq is None or _only_unknown(prereq)) and coreq is None:
        status = "unparsed"
    elif unknown or notes:
        status = "partial"
    else:
        status = "parsed"
    return ParsedRequisites(prereq, coreq, status, notes)


def _course_codes(node: Optional[Requisite]) -> set[str]:
    if node is None:
        return set()
    if node.kind == "course":
        return {node.code}
    if node.kind in ("all", "any"):
        return set().union(*(_course_codes(i) for i in node.items))
    return set()


def _only_unknown(node: Requisite) -> bool:
    if node.kind == "condition":
        return not node.recognized
    if node.kind in ("all", "any"):
        return all(_only_unknown(i) for i in node.items)
    return False


def describe(node: Optional[Requisite]) -> str:
    """Human-readable rendering, used in explanations and tests."""
    if node is None:
        return "none"
    if node.kind == "course":
        s = node.code
        if node.min_grade:
            s += f" (≥{node.min_grade})"
        if node.concurrent_ok:
            s += " [may be concurrent]"
        return s
    if node.kind in ("all", "any"):
        joiner = " AND " if node.kind == "all" else " OR "
        return "(" + joiner.join(describe(i) for i in node.items) + ")"
    if node.kind in ("placement", "permission"):
        return node.kind.upper()
    return f"<{'condition' if node.recognized else 'UNPARSED'}: {node.text}>"
