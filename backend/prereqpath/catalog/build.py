"""Build the local catalog dataset from catalog.unc.edu.

    python -m prereqpath.catalog.build courses              # every subject page
    python -m prereqpath.catalog.build courses --subjects math stor
    python -m prereqpath.catalog.build programs             # index + every program page
    python -m prereqpath.catalog.build programs --only mathematics-major-ba
    python -m prereqpath.catalog.build report               # parse coverage

Raw HTML is cached under data/raw/ (git-ignored); parsed JSON under
data/catalog/<catalog-year>/ is committed and is what the app reads.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from .. import DATA_DIR
from .courses import parse_subject_page, subject_pages
from .fetch import BASE, CatalogFetcher
from .programs import discover_programs, parse_program_page

CURRENT_CATALOG_YEAR = "2026-2027"   # the live site; earlier years need legitimately obtained archives


def catalog_dir(year: str) -> Path:
    return DATA_DIR / "catalog" / year


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_courses(path: Path, header: dict, courses: list[dict]) -> None:
    """One course per line: compact on disk, readable in git diffs."""
    compact = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    head = compact(header)[:-1]
    body = ",\n".join(compact(c) for c in courses)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{head},"courses":[\n{body}\n]}}\n', encoding="utf-8")


def build_courses(fetcher: CatalogFetcher, year: str, subjects: list[str] | None) -> dict:
    index = fetcher.fetch(BASE + "/courses/")
    paths = subject_pages(index.html)
    if subjects:
        wanted = {s.lower() for s in subjects}
        paths = [p for p in paths if p.strip("/").split("/")[-1] in wanted]
    summary = collections.Counter()
    problems: dict[str, list[str]] = {}
    for path in paths:
        page = fetcher.fetch(BASE + path)
        subject = path.strip("/").split("/")[-1]
        courses, issues = parse_subject_page(page.html, page.url, year, page.retrieved_at)
        if issues:
            problems[subject] = issues
        summary.update(c.requisites_status for c in courses)
        _write_courses(catalog_dir(year) / "courses" / f"{subject}.json",
                       {"catalog_year": year, "source_url": page.url, "retrieved_at": page.retrieved_at,
                        "page_sha256": page.sha256}, [c.model_dump(exclude_none=True) for c in courses])
        print(f"{subject:>6}: {len(courses):4d} courses {'(cached)' if page.from_cache else ''}")
    return {"subjects": len(paths), "requisite_status": dict(summary), "problems": problems}


def build_programs(fetcher: CatalogFetcher, year: str, only: list[str] | None) -> dict:
    index = fetcher.fetch(BASE + "/undergraduate/programs-study/")
    listings, skipped = discover_programs(index.html, year)
    _write(catalog_dir(year) / "programs" / "index.json",
           {"catalog_year": year, "source_url": index.url, "retrieved_at": index.retrieved_at,
            "skipped_non_undergraduate": skipped,
            "programs": [p.model_dump(exclude_none=True) for p in listings]})
    targets = [p for p in listings if not only or p.id in only]
    status = collections.Counter()
    for listing in targets:
        page = fetcher.fetch(listing.url)
        program = parse_program_page(page.html, listing, page.retrieved_at)
        status[program.verification.status] += 1
        _write(catalog_dir(year) / "programs" / "parsed" / f"{listing.id}.json", program.model_dump(exclude_none=True))
    kinds = collections.Counter(p.kind for p in listings)
    return {"discovered": len(listings), "kinds": dict(kinds), "parsed": len(targets),
            "parse_status": dict(status), "skipped_non_undergraduate": skipped}


def report(year: str) -> dict:
    statuses = collections.Counter()
    total = 0
    for path in sorted((catalog_dir(year) / "courses").glob("*.json")):
        for c in json.loads(path.read_text(encoding="utf-8"))["courses"]:
            total += 1
            statuses[c.get("requisites_status", "none")] += 1
    with_text = total - statuses["none"]
    return {"courses": total, "requisite_status": dict(statuses),
            "fully_parsed_share_of_courses_with_requisites":
                round(statuses["parsed"] / with_text, 3) if with_text else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["courses", "programs", "report"])
    ap.add_argument("--year", default=CURRENT_CATALOG_YEAR)
    ap.add_argument("--subjects", nargs="*")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--refresh", action="store_true", help="ignore the raw HTML cache")
    ap.add_argument("--offline", action="store_true", help="use only cached HTML")
    args = ap.parse_args()
    if args.year != CURRENT_CATALOG_YEAR and args.what != "report":
        raise SystemExit("Only the live catalog year can be fetched; archived years need a legitimately obtained copy.")
    fetcher = CatalogFetcher(DATA_DIR / "raw" / args.year, refresh=args.refresh, offline=args.offline)
    if args.what == "courses":
        result = build_courses(fetcher, args.year, args.subjects)
    elif args.what == "programs":
        result = build_programs(fetcher, args.year, args.only)
    else:
        result = report(args.year)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
