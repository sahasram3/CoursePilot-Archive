"""AP and IB credit from catalog.unc.edu/policies-procedures/credit-evaluation/.

Each table row is: exam, minimum score, awarded UNC courses, credit hours.
Awards such as "MATH 110P" are placement credit: not catalog courses, but
prerequisites reference them ("MATH 110 or 110P"), so they are kept as codes.
"""
from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

URL = "https://catalog.unc.edu/policies-procedures/credit-evaluation/"
TABLES = {"Advanced Placement Exam Scores": "AP", "International Baccalaureate Scores": "IB"}
CODE_RE = re.compile(r"\b([A-Z]{2,4})\s+(\d{2,3}[A-Z]{0,2})\b")


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\xa0", " ")).strip()


def parse_exam_credit(html: str, catalog_year: str, retrieved_at: str | None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for table in soup.select("table.sc_sctable"):
        heading = table.find_previous(["h2", "h3", "h4"])
        kind = TABLES.get(_text(heading) if heading else "")
        if not kind:
            continue
        for tr in table.select("tr"):
            cells = [_text(td) for td in tr.find_all("td")]
            if len(cells) != 4 or not re.fullmatch(r"\d+", cells[1]):
                continue          # header rows ("Column 1", "Exam | Minimum Score | ...")
            exam, score, awarded, hours = cells
            codes = [f"{a} {b}" for a, b in CODE_RE.findall(awarded)]
            other = [p.strip() for p in awarded.split(",") if p.strip() and not CODE_RE.search(p)]
            try:
                hours_value = float(hours)
            except ValueError:
                hours_value = 0.0
            verbatim = " | ".join(cells)
            rows.append({
                "type": kind, "exam": exam, "min_score": int(score), "courses": codes,
                "other_credit": other, "hours": hours_value,
                "source": {"url": URL, "catalog_year": catalog_year, "section": heading and _text(heading),
                           "text": verbatim, "retrieved_at": retrieved_at,
                           "sha256": hashlib.sha256(verbatim.encode("utf-8")).hexdigest()},
            })
    return rows


def award_for(rows: list[dict], kind: str, exam: str, score: int) -> dict | None:
    """The award for the highest listed minimum score at or below `score`.
    Rows for one exam are read as alternatives (a higher score replaces a lower
    award), which is how the catalog table is laid out."""
    matches = [r for r in rows if r["type"] == kind and r["exam"] == exam and r["min_score"] <= score]
    return max(matches, key=lambda r: r["min_score"]) if matches else None
