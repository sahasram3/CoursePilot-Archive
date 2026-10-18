# PreReqPath

Semester-by-semester degree planning for UNC-Chapel Hill undergraduates, built from the
official 2026–2027 catalog. A student picks a program, enters the courses they have credit
for, chooses a graduation term, and gets an actual plan: every course in a specific term,
prerequisites in order, full-time loads, and 120 hours, with each requirement linked to the
catalog text it came from.

> **Plans are provisional.** PreReqPath is an independent student project, not an official
> UNC degree audit. It never labels a plan graduation-certified. Confirm with your advisor
> and Tar Heel Tracker.

## Status (v0.10, Mathematics B.A. vertical slice)

| Area | State |
|---|---|
| Course catalog | **All 156 subjects, 10,673 courses** with credits, IDEAs attributes, cross-listings and requisites. Requisite text parsed into AND/OR trees for 80% of courses that have requisites; the rest are explicitly flagged `partial`/`unparsed`. |
| Program index | **All 202 undergraduate majors, minors, tracks and concentrations** discovered from the official index. |
| Plannable programs | **Mathematics B.A.**: requirements and the 41 course requisites its planner can reach are hand-verified against the catalog text. Other programs are listed but not yet plannable. |
| Planner | OR-Tools CP-SAT; sub-second for the Math B.A.; explains infeasible requests. |
| App | FastAPI backend + React/TypeScript frontend. |

## Run it

Requires Python 3.11+ and Node 18+.

```bash
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"      # macOS/Linux: .venv/bin/pip
cd frontend && npm install && npm run build && cd ..
cd backend && ../.venv/Scripts/python -m uvicorn prereqpath.api:app --port 8000
```

Open http://127.0.0.1:8000. For frontend development, run the API as above and
`npm run dev` in `frontend/` (Vite on :5173, proxying `/api`).

Tests: `cd backend && ../.venv/Scripts/python -m pytest` (66 tests, all on real catalog data);
`cd frontend && npm run typecheck`.

## How it works

```
catalog.unc.edu ──fetch.py──▶ data/raw/ (cache, git-ignored)
                 (robots.txt, 1.5 s delay, /archives/ never crawled)
      │
      ├─ courses.py + requisites.py ─▶ data/catalog/<year>/courses/*.json
      └─ programs.py ────────────────▶ data/catalog/<year>/programs/{index.json, parsed/*.json}
                                            │
data/verified/<year>/ (hand-verified overlays, pinned to source text hashes)
                                            │
store.py ──▶ planner/engine.py (CP-SAT) ──▶ planner/validate.py (independent re-check) ──▶ api.py ──▶ React UI
```

* **Provenance everywhere.** Each course and requirement keeps its source URL, catalog year,
  verbatim source text and SHA-256, and a verification status: `verified`, `parsed`,
  `uncertain`, or `needs_reverification` (the catalog text changed after review).
* **Requisites** become trees of course atoms (with minimum grades and "may be concurrent"),
  placement/permission tokens, and conditions. Ambiguous wording ("A and B or C") is
  flagged rather than silently resolved; unparseable text becomes an explicit condition.
* **The solver** (`x[course, term]` booleans) enforces prerequisite order, corequisites,
  requirement choice with no double counting inside a program, 12–18 hours per term,
  120 hours with the B.A. 45-hour single-subject cap, locks and exclusions. It pulls in
  missing prerequisites automatically and treats minimum grades on *planned* courses as
  stated contingencies. Unresolved requirements are reported, never counted as met.
* **Infeasible requests** are explained with the unsatisfiable requirement set, the
  credit-hour capacity, the binding prerequisite chain, and re-solved "what would work"
  options (later graduation, summers, removing locks, department placement).
* **Every returned plan is re-validated** by a separate pure-Python checker.

### Rebuilding catalog data

```bash
cd backend
../.venv/Scripts/python -m prereqpath.catalog.build courses      # ~4 min, polite
../.venv/Scripts/python -m prereqpath.catalog.build programs     # index + program pages
../.venv/Scripts/python -m prereqpath.catalog.build report       # parse coverage
```

Only the live catalog year can be fetched. Earlier entering cohorts (Fall 2022–Spring 2026
use archived IDEAs editions; earlier students use Making Connections) need legitimately
obtained archived catalogs: `/archives/` is disallowed by robots.txt and is never crawled.

### Verifying a program

Write `data/verified/<year>/programs/<program-id>.json` (see `mathematics-major-ba.json`):
the requirement tree, verbatim source quotes, interpretation notes, and the
`verified_requirements_sha256` of the parsed requirements text. If UNC later edits the
page, the program automatically drops to `needs_reverification`.

## Known limitations

* Only the Mathematics B.A. is plannable. Double majors/minors are supported by the data
  model and solver structure but need more verified programs.
* IDEAs in Action Gen Eds are **reserved as placeholder hours**, not assigned to courses yet.
  B.A. Supplemental Gen Ed is not modeled.
* Course offering terms are not modeled: every course is assumed available each Fall and Spring.
* GPA rules (2.000 overall and in the major core) depend on future grades and are reported only.
* Requirements for students who entered before Fall 2026 use 2026–27 requirements with a warning.
* Hand verification was performed by an AI-assisted review against the published catalog text,
  not by UNC.

## Repository history

The pre-rebuild ChatGPT-era prototype (v0.7–v2.9) is preserved on the
`backup/v29-prototype` branch.
