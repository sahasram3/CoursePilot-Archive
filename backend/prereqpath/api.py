"""HTTP API (FastAPI). Also serves the built React app from frontend/dist.

    uvicorn prereqpath.api:app --port 8000

Environment (all optional):
    PREREQPATH_DATA_DIR          catalog data directory (default: <repo>/data)
    PREREQPATH_MAX_CONCURRENT    simultaneous plan solves (default 2); extra requests get HTTP 503
    PREREQPATH_CORS_ORIGINS      comma-separated origins, only if the frontend is hosted elsewhere
    PREREQPATH_MAX_ALTERNATIVES  cap on alternative plans per request (default 3; 1 on CPU-capped hosts)
"""
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import REPO_ROOT
from .catalog.requisites import describe
from .planner import plan as run_plan
from .planner.engine import PlanningError, _token_nodes, prepare
from .planner.schemas import PlanRequest, PlanResponse
from .policy import policies
from .store import available_catalog_years, get_store

DEFAULT_YEAR = "2026-2027"
# Each solve uses several CPU-seconds; cap concurrency so a burst degrades to clear
# "busy, retry" responses instead of a stalled server.
SOLVE_SLOTS = threading.BoundedSemaphore(int(os.environ.get("PREREQPATH_MAX_CONCURRENT", "2")))
# Each extra alternative is another solve; CPU-capped hosts can limit it.
MAX_ALTERNATIVES = max(1, int(os.environ.get("PREREQPATH_MAX_ALTERNATIVES", "3")))


@asynccontextmanager
async def lifespan(_: FastAPI):
    for year in available_catalog_years():
        get_store(year)          # load the catalog once at startup, not on the first request
    yield


app = FastAPI(title="CoursePilot", version="1.0.0", lifespan=lifespan,
              description="Provisional semester-by-semester planning from the UNC-Chapel Hill catalog. "
                          "Not an official degree audit.")
app.add_middleware(GZipMiddleware, minimum_size=1024)
if os.environ.get("PREREQPATH_CORS_ORIGINS"):
    app.add_middleware(CORSMiddleware, allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
                       allow_origins=[o.strip() for o in os.environ["PREREQPATH_CORS_ORIGINS"].split(",") if o.strip()])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


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
    if request.alternatives > MAX_ALTERNATIVES:
        request = request.model_copy(update={"alternatives": MAX_ALTERNATIVES})
    if not SOLVE_SLOTS.acquire(timeout=15):
        raise HTTPException(503, "The planner is busy right now. Please try again in a few seconds.")
    try:
        return run_plan(request)
    except PlanningError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        SOLVE_SLOTS.release()


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
