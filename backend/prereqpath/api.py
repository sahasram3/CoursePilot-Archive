"""HTTP API (FastAPI). Also serves the built React app from frontend/dist.

    uvicorn prereqpath.api:app --port 8000
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import REPO_ROOT
from .catalog.requisites import describe
from .planner import plan as run_plan
from .planner.engine import PlanningError, _token_nodes, prepare
from .planner.schemas import PlanRequest, PlanResponse
from .policy import policies
from .store import available_catalog_years, get_store

app = FastAPI(title="PreReqPath", version="0.10.0",
              description="Provisional semester-by-semester planning from the UNC-Chapel Hill catalog. "
                          "Not an official degree audit.")
DEFAULT_YEAR = "2026-2027"


def _store(year: str):
    if year not in available_catalog_years():
        raise HTTPException(404, f"Catalog year {year} is not available")
    return get_store(year)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/catalog-years")
def catalog_years():
    return {"catalog_years": available_catalog_years(), "default": DEFAULT_YEAR}


@app.get("/api/programs")
def programs(catalog_year: str = DEFAULT_YEAR):
    store = _store(catalog_year)
    items = []
    for listing in sorted(store.listings.values(), key=lambda p: p.name):
        program = store.program(listing.id)
        items.append({**listing.model_dump(), "plannable": program is not None,
                      "verification": program.verification.status if program else None})
    return {"catalog_year": catalog_year, "programs": items,
            "counts": {"discovered": len(items), "plannable": sum(i["plannable"] for i in items)}}


@app.get("/api/programs/{program_id}")
def program_detail(program_id: str, catalog_year: str = DEFAULT_YEAR):
    store = _store(catalog_year)
    program = store.program(program_id)
    if program is not None:
        return {"plannable": True, "program": program.model_dump()}
    listing = store.listings.get(program_id)
    if listing is None:
        raise HTTPException(404, "Unknown program")
    return {"plannable": False, "program": listing.model_dump()}


@app.get("/api/programs/{program_id}/placements")
def placements(program_id: str, catalog_year: str = DEFAULT_YEAR):
    """Placement/permission options that appear in this program's prerequisite chains."""
    store = _store(catalog_year)
    if store.program(program_id) is None:
        raise HTTPException(404, "Program not plannable")
    ctx = prepare(PlanRequest(catalog_year=catalog_year, programs=[program_id]), store)
    options = {}
    for course in ctx.schedulable.values():
        for token in _token_nodes(course.prerequisites):
            if token.startswith("PLACEMENT:"):
                code = token.split(":", 1)[1]
                options[token] = {"token": token, "course": code,
                                  "title": store.courses[code].title if code in store.courses else "",
                                  "label": f"Placed into {code} by the department"}
    return {"placements": sorted(options.values(), key=lambda o: o["course"])}


@app.get("/api/courses/search")
def course_search(q: str = Query(..., min_length=1, max_length=40), catalog_year: str = DEFAULT_YEAR,
                  limit: int = Query(15, ge=1, le=50)):
    store = _store(catalog_year)
    return {"results": [{"code": c.code, "title": c.title, "credits_min": c.credits_min,
                         "credits_max": c.credits_max} for c in store.search(q, limit)]}


@app.get("/api/courses/{code}")
def course_detail(code: str, catalog_year: str = DEFAULT_YEAR):
    store = _store(catalog_year)
    course = store.course(code)
    if course is None:
        raise HTTPException(404, "Course not found in this catalog year")
    return {**course.model_dump(), "prerequisites_text": describe(course.prerequisites),
            "corequisites_text": describe(course.corequisites) if course.corequisites else None}


@app.get("/api/exams")
def exams(catalog_year: str = DEFAULT_YEAR):
    """AP/IB exams from the catalog credit table, with every award row for display."""
    store = _store(catalog_year)
    return {"source_url": "https://catalog.unc.edu/policies-procedures/credit-evaluation/",
            "exams": store.exam_options(),
            "awards": [{k: r[k] for k in ("type", "exam", "min_score", "courses", "other_credit", "hours")}
                       | ({"note": r["note"]} if "note" in r else {}) for r in store.exam_awards]}


@app.get("/api/policies")
def policy_list(catalog_year: str = DEFAULT_YEAR):
    return {"catalog_year": catalog_year, "policies": policies(catalog_year)}


@app.post("/api/plan", response_model=PlanResponse)
def make_plan(request: PlanRequest):
    if request.catalog_year not in available_catalog_years():
        raise HTTPException(422, f"Catalog year {request.catalog_year} is not available")
    try:
        return run_plan(request)
    except PlanningError as exc:
        raise HTTPException(422, str(exc)) from exc


# ------------------------------------------------------------- web app
DIST: Optional[Path] = REPO_ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
