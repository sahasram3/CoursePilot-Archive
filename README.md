# PreReqPath AI v0.8 — UNC Mathematics B.A. pilot

This version preserves v0.7 and adds a **source-backed transcription of the 2026–2027 Mathematics B.A. program core**. It does **not** claim to generate a degree-compliant schedule.

## What was checked

The live UNC catalog page displays the heading **2026–2027 Academic Catalog**. Its Mathematics B.A. requirements table lists 33 hours, five fixed courses, two choose-one groups, and three additional MATH courses above 500 (9 hours), with a special lab exception. The page also documents a conditional STOR 215 substitution for MATH 381.

Source: https://catalog.unc.edu/undergraduate/programs-study/mathematics-major-ba/

`data/math_ba_2026_evidence.json` preserves the structured transcription and unresolved items. `src/math_ba_2026.py` provides a conservative **partial core audit** that never certifies graduation. Individual prerequisite rules, upper-level course eligibility, GPA, Gen Ed, university residency, overlap, and term offerings are **not yet verified or implemented**.

## Run

```bash
python -m unittest discover -s tests -v
python -c "from src.math_ba_2026 import source_record; print(source_record())"
```

## Next engineering tasks

1. Verify individual course descriptions and prerequisite logic, including OR, grade, and placement clauses.
2. Implement upper-level elective eligibility and the special lab-bundle exception with explicit credit accounting.
3. Model UNC-wide degree requirements and exclusivity/double-counting rules.
4. Only then enable actual full-horizon degree planning for this pilot program.

**Never treat this program-core audit as an official UNC degree audit.**

## v0.9 — University-wide architecture and prerequisite graph

**Scope:** PreReqPath targets every UNC Chapel Hill undergraduate major and minor in the 2026–2027 catalog, including separately listed tracks/concentrations. Mathematics is the first test case, **not a scope restriction**. The official index currently lists programs beyond Mathematics, including Biology, Computer Science, Data Science, Statistics and Analytics, and Neuroscience. The registry discovery function `src.program_coverage.registry_from_index(html)` works on *all* linked program pages, not a hardcoded Math list. It deliberately records `plan_ready=false` until requirements, course rules, and degree policies are verified.

**New prerequisite engine:** `src.prerequisite_graph` models conjunctions of disjunctions (AND of OR clauses), grade thresholds, explicitly granted placement/permission tokens, course-to-course dependency edges, and term-by-term validation. `src.math_prerequisites_2026` transcribes a **reviewed subset of 16 MATH course descriptions** from https://catalog.unc.edu/courses/math/ (2026–2027 catalog). MATH 347 is *excluded* from the graph because its complex grouped prerequisite wording requires additional encoding. MATH 231 is not yet included because its placement/prerequisite conditions require separate review. No course in this subset should be mistaken for an approved full-degree plan.

**Generate an index registry (when network access is available):**

```bash
python -c "import requests; from src.program_coverage import save_registry; from src.catalog import INDEX; h=requests.get(INDEX,timeout=30).text; r=save_registry(h,'data/all_unc_programs_unreviewed.json'); print(r['total_discovered'])"
```

The index crawl has **not** been executed successfully in this sandbox, so no complete catalog-wide snapshot or complete program-count claim is made. Do not infer `plan_ready` from `discovered`. Respect the catalog's robots.txt and access policies before automated retrieval.

**Test:** `python -m unittest discover -s tests -v` (40 tests at this release).

**Remaining work:** verify all course prerequisite records and program requirements across all departments, resolve grouped Boolean conditions, add university-wide Gen Ed, grades, residency, overlaps, permission, availability, and full-horizon optimizer integration. The new graph validator is separate from the older scheduler until that integration is completed.

## v1.0 — Degree choice → prerequisite graph integration

`src.graph_optimizer.optimize_graph` performs prerequisite-aware backtracking across **all supplied remaining terms** with AND-of-OR clauses, completed-course grades, explicit permissions, course locks, exact reviewed credit values, and multiple alternative schedules. `src.degree_optimizer.generate_with_prerequisite_graph` bridges verified degree requirement choices to that planner for **any** reviewed UNC program. It fails closed on missing course rules. A zero minimum-credit setting means only modeled degree courses are scheduled; it is not an assertion that a student can enroll below UNC's full-time requirement. Nonzero minima require actual supplied courses; no filler credits are fabricated. Search has a finite state cap and reports truncation.

**Important limits:** Catalog-wide discovery remains an architecture feature, not a completed verified import. The planner does not automatically insert missing prerequisite courses, does not resolve course offering availability, wildcard elective groups, general education, major/minor overlap, residency, admissions, permission approvals, or certify graduation. Course prerequisite records for Mathematics are still partial. The bridge only accepts already reviewed and explicitly enumerated degree requirement groups.

### Synthetic demonstration

```bash
python -m unittest discover -s tests -q
python - <<'PY'
from src.graph_optimizer import optimize_graph, PlanningRequest
from src.prerequisite_graph import CourseRule, Alternative
from src.planner import terms
u='https://catalog.unc.edu/courses/math/'
a=CourseRule('DEMO 101',3,(),u,'Synthetic test course')
b=CourseRule('DEMO 201',3,((Alternative('DEMO 101'),),),u,'Synthetic test course')
result=optimize_graph({'DEMO 101':a,'DEMO 201':b},terms(2026,'Fall',2027,'Spring'),PlanningRequest(('DEMO 101','DEMO 201')),limit=2)
for option in result['alternatives']: print(option['terms'])
PY
```

Synthetic courses in the demonstration are **not UNC catalog courses**.

## v1.1 — Student-facing local web prototype

Run from the project root with **Python 3.10+**, no additional web framework:

```bash
python server.py
```

Open `http://127.0.0.1:8765` in your browser. The frontend communicates with a local Python API. There is no cloud deployment, login, or storage of student records. The app currently offers **only a six-course Mathematics demonstration**; other named programs are intentionally blocked. It does not assert degree completion or verified course availability.

API: `GET /api/programs`, `GET /api/courses`, `POST /api/plan`. Tests: `python -m unittest discover -s tests -v`.

**Next:** verified university-wide catalog data, complete degree rules and course offerings, enrollment constraints, and then production hosting.

## v1.2: University-wide catalog registry import

The app now supports discovery of **all major/minor entries present in a supplied official UNC catalog index HTML file**, and the UI supports choosing valid one-/two-major combinations with optional minors. This is a discovery and selection feature, **not** full academic-plan coverage. A discovered entry remains unverified and cannot generate a purported graduation plan.

To import the official index without relying on a crawler, open https://catalog.unc.edu/undergraduate/programs-study/ in your browser, save the **complete HTML page** (not a screenshot), and run from the project root:

```bash
python -m src.catalog_registry --html path/to/saved_unc_index.html --output data/unc_program_registry.json
python server.py
```

The importer requires at least 100 major/minor entries by default to avoid silently accepting a partial page. The source HTML must contain links to the official program pages. You can lower the threshold for development fixtures with `--minimum 1`. The registry records discovery status, not requirement approval. `GET /api/coverage` exposes coverage counts; `POST /api/validate-selection` validates combination structure without falsely asserting program-specific compatibility.

**Environment note:** Network DNS resolution to UNC failed during this build. Accordingly the ZIP does not claim to contain a completed live catalog import, and the web UI displays the limited fallback entries until the official index is imported. Requirements and prerequisites for every major/minor still need individual validation.

## v1.3 — University-wide source-evidence review pipeline

`src.review_pipeline` processes a full imported registry against a directory of locally saved official UNC program HTML pages. It extracts page headings, requirement tables, text excerpts, SHA-256 source fingerprints, year-evidence flags, and review status. Missing pages remain visible as `source_missing` rather than disappearing. With `--previous`, changed source pages are flagged for renewed review. **No extracted requirement is automatically approved for scheduling.**

```bash
python -m src.review_pipeline --registry data/unc_program_registry.json --html-dir saved_program_pages --output data/program_review_queue.json
python -m src.review_pipeline --registry data/unc_program_registry.json --html-dir saved_program_pages --previous data/program_review_queue.json --output data/program_review_queue_new.json
python -m unittest discover -s tests -q
```

Name each saved HTML page `<program-id>.html` (e.g. `biology-major-bs.html`). The previous milestone's catalog index importer generates the program IDs. The importer does not fetch URLs automatically; the user's local machine must have actual UNC HTML files available, obtained consistently with site terms and robots policy. The `2026–2027 Academic Catalog` phrase is an evidence check, not proof that the full program rules are correctly transcribed. An unchanged fingerprint also does not mean a page is accurate or current.

**Coverage in this ZIP:** No full university-wide UNC source snapshot is bundled. Discovery, source ingestion, and human review are distinct steps; the existing six-course Mathematics demonstration is still not a graduation audit. The new test fixtures contain synthetic text and are not UNC academic rules.

## v1.4 — Candidate rule interpretation (not approval)

The new `src.rule_candidates` module converts the v1.3 source-evidence review queue into structured **review candidates**, retaining exact table coordinates and source SHA-256 fingerprints. It recognizes straightforward course-and-credit rows, alternative course rows, elective/choice language, variable credit ranges, and flags grade, prerequisite, corequisite, residency, substitution, and double-counting prose. Ambiguous rows are deliberately **not** converted to definitive degree requirements. The module makes no automatic approval decisions and does not modify the scheduling engine.

Run from the project root after obtaining the actual UNC HTML and creating the evidence queue:

```bash
python -m src.rule_candidates --review-queue data/program_review_queue.json --output data/rule_candidate_queue.json
python -m unittest discover -s tests -q
```

The package includes synthetic unit-test fixtures only; it does not include a university-wide catalog snapshot. `programs_with_candidates` means candidate evidence exists, **not** that the program is supported for planning. All 77 tests pass on the bundled code.

## v1.5: Human requirement approval workflow

New module: `src/approval_workflow.py`. It consumes v1.4 candidate queues, creates stable source-bound candidate IDs, supports named-human review with a verbatim evidence quote and interpretation rationale, and exports **partial** reviewed rule records. No program is ever marked degree-plan-ready by this workflow. All rules remain partial until a separate whole-degree audit is implemented. A source fingerprint change invalidates existing approvals via `reconcile_sources`.

```bash
python -m src.approval_workflow init --candidates data/rule_candidate_queue.json --output data/reviews.json
python -m src.approval_workflow report --state data/reviews.json
# After a human has checked the actual official page and selected an ID from reviews.json:
python -m src.approval_workflow approve --state data/reviews.json --program PROGRAM_ID --candidate CANDIDATE_ID --reviewer 'Reviewer Name' --quote 'EXACT TEXT FROM ROW' --kind ALL --courses 'MATH 231' --rationale 'Checked the requirement against the catalog table'
python -m src.approval_workflow export --state data/reviews.json --output data/partial_approved_rules.json
python -m unittest discover -s tests -q
```

`approve` is a human attestation command, not a source verification service. No real catalog candidates are automatically approved or certified. Do not publish the review state as proof of academic correctness. The command is local-only; no publicly exposed approval API is provided.

## v1.6 — Whole-program completeness gate

New `src/whole_program.py` provides a fail-closed **internal review** checklist for every program, not just Mathematics. It requires a human to enumerate and review source sections, resolve all extracted candidate requirements, and explicitly document all 13 academic rule categories, including restrictions and degree-wide rules. It invalidates readiness when the source fingerprint changes or a candidate is pending/stale. `internally_reviewed_for_planning` means only that the human checklist passed; it is **not official degree certification** and does not guarantee the optimizer implements all those rules. No bundled UNC program passes this gate automatically.

Example coverage report (after a real human has created and populated checklist JSON):

```bash
python -m src.whole_program --reviews data/reviews.json --checklists data/whole_program_checklists.json --output data/whole_program_coverage.json
python -m unittest discover -s tests -q
```

Checklist format is produced by `create_checklist(program, source_sections=[...])`. An authorized human reviewer must populate all sections and category evidence and call `attest(...)`. The library never auto-attests. The CLI above only reports coverage and never approves a program. Synthetic tests demonstrate the gate, not any UNC degree validation.

## v1.7 — Real-degree planning eligibility gate

`src/planning_eligibility.py` combines whole-program human completeness review with explicit planner capability checks. A complete catalog review alone does **not** enable degree planning: every verified requirement category must be supported by the planner, each required course needs reviewed rules, and multi-program combinations require separate human-attested compatibility and double-counting review. Missing data always blocks eligibility. `GET /api/planning-eligibility` reports that no full programs are currently eligible. `POST /api/degree-plan` refuses to produce a degree plan, returning the eligibility blockers (HTTP 422). The legacy `POST /api/plan` remains an explicitly limited six-course Mathematics demonstration, not a degree plan. No human attestation has been fabricated.

Test with `PYTHONPATH=. python -m unittest discover -s tests -q` (111 passing as of v1.7). The capability map deliberately marks university-wide Gen Ed, corequisites, degree credit totals, overlap, and other unsupported constraints as not implemented. Future work must implement and independently test each capability before enabling real degree plans.

## v1.8 — Cross-program degree policy and correctness regression fixes

`src/degree_policy.py` introduces a source-gated, provisional audit for total credits,
General Education selection groups, residency credits and maximum shared courses
across majors/minors. The policy **must** be explicitly reviewed against an
official UNC source; this release does not insert guessed UNC thresholds.
Credit hours are counted once per distinct course. Missing course credit data,
unverified program-course mappings, or unspecified residency/overlap limits block
eligibility. Callers are responsible for supplying genuinely verified course-credit
records; this module cannot independently authenticate arbitrary caller data.

The prerequisite optimizer now rejects schedules that depend on an unknown
**future minimum grade** rather than pretending a future student will earn it.
This conservative limitation can reject some plans that would become feasible
with a successful future grade; future versions should expose conditional plans
with explicit contingencies, not guarantee them.

Run: `python -m unittest discover -s tests -q` (122 tests).

**Not done:** this module is not yet connected to `/api/degree-plan`, which
remains fail-closed. No UNC university-wide policies have been human-reviewed
or imported, and no degree is certified. The new tests use synthetic policies.


## v1.9 — Roadmap-wide audit integration and residency regression

`src/roadmap_audit.py` now runs a degree-wide policy audit **for every** alternative
returned by the prerequisite-aware optimizer. The existing `/api/plan` six-course
Mathematics demo exposes `degree_audit.blockers` and the browser displays them.
Without a trusted reviewed UNC policy, the demo explicitly reports
`reviewed_degree_policy_missing`. The `/api/degree-plan` endpoint remains disabled.

**Bug fixed:** earlier residency logic incorrectly counted *planned future* courses
as already earned UNC-resident credit. Only completed courses may count as earned
residency credits; future credits require a separate conditional forecast model.
The corresponding prior test was corrected because it encoded the old bug.

**Trust boundary:** do not accept a student-supplied `Policy(status='reviewed')`,
`verified_program_mapping=True`, or source metadata as evidence of human approval.
Real degree planning must load these from a protected, independently reviewed
server-side source and check catalog freshness, full program coverage and all
unsupported constraints. The provisional audit's `eligible` field describes only
the narrow modeled policy, never full degree eligibility.

Run `python -m unittest discover -s tests -q` (128 passing tests).

## v2.0 — Trusted policy and real-planning security boundary

`src/trusted_policy_store.py` loads policy records **only from server-owned files** with a deployment-pinned SHA-256 manifest. The pin is supplied by the operator using `PREREQPATH_TRUSTED_MANIFEST_SHA256`, never by a student request. A policy must have matching identifier, 2026–2027 catalog year, reviewer provenance, source fingerprint, and explicit residency/overlap thresholds. The repository intentionally ships **no approved policy or manifest**. Hash pinning provides file integrity against accidental or unauthorized changes to one file; it does not prove that a reviewer is qualified, that catalog interpretations are correct, or that UNC endorsed the record. A compromised deployment operator could replace both the manifest and pin.

`src/degree_plan_gate.py` validates selected programs against server-owned review records and trusted policy availability, and **continues to block real degree plans** while the complete degree solver remains unvalidated. The `/api/degree-plan` endpoint ignores any client-supplied approval or policy flags. `/api/planning-eligibility` exposes a non-sensitive policy availability summary. The Math-only sequence demo remains provisional.

**Open issues:** Actual UNC catalog import and rule review; trusted reviewer access control and audit logs; complete degree solver, nested requirements and university-wide double counting; authentic transfer/credit verification; actual future course availability; comprehensive Gen Ed, residency and admission policies. No real UNC degree program is enabled for graduation planning.

## v2.1: Official UNC university-wide policy evidence

The new `data/unc_official_2026_policy_facts.json` is a source-backed transcription of selected **2026–2027** undergraduate degree rules from the official UNC catalog. `src/unc_official_policy_2026.py` contains a conservative partial auditor, with twelve regression tests. Sources:

- https://catalog.unc.edu/undergraduate/degree-requirements/
- https://catalog.unc.edu/undergraduate/ideas-in-action/

**Verified against published source text, not independently approved:** This research and transcription was performed in this project, not independently signed off by a UNC registrar or second qualified reviewer. The data is intentionally tagged `not_independently_reviewed` and is NOT installed in the trusted-policy approval store. No degree plan is certified or enabled.

Key catalog rules include minimum 120 semester hours (some B.S. curricula require more), at least 45 eligible UNC hours, minimum 2.000 cumulative UNC GPA, at least half of major-core courses AND hours at UNC, at least nine minor-core UNC hours, and **strictly more than half** of the courses AND hours of EACH major/minor core exclusive to that program. These are not reducible to one global maximum number of shared courses. The old `max_shared_program_courses` model in `degree_policy.py` and `trusted_policy_store.py` is therefore unsuitable as the final UNC policy representation and must not be used to certify plans.

**Cohort trap:** The 2026–2027 IDEAs page explicitly says its listed requirements apply to students starting Fall 2026; students starting Fall 2022 through Spring 2026 use archived editions. Catalog year and entrance cohort cannot be conflated.

**Source discrepancy:** A search-indexed older PDF mentioned a 24-of-last-30 UNC-credit rule, but that language was not found on the live 2026–2027 degree requirements HTML page. We have *not* imported it as a current verified rule. Further authoritative reconciliation is required.

The auditor is provisional and never returns `degree_certified=True` or `eligible=True`. Course credits and program core membership remain caller-supplied and must be authenticated separately.

## v2.2 — Policy audit integration and accuracy hardening

- New `src/policy_v22.py` evaluates source-backed university-wide policy **provisionally**, including strictly-majority exclusive core credits **and** courses, UNC residency, cumulative/core GPA unknowns, cohort-specific Gen Ed, duplicate courses, and higher B.S. minima.
- `/api/plan` demo alternatives now contain `official_policy_audit` using **server-side** verified course credit values, but unknown student course origins. Missing origin, cohort, program mapping and independent review are explicitly blocked. It never certifies graduation.
- `GET /api/policy-status` exposes source provenance and disabled production status.
- The legacy `degree_policy.py` flat shared-course threshold remains for backward compatibility only. **Do not use it for UNC certification.** Its older audit is likewise provisional.
- New regression tests cover duplicate credits, strictly greater-than-half exclusivity, future versus earned credits, unknown origins, NaN GPA, and missing B.S. program minima.
- Independent academic review and catalog-complete Gen Ed/program-specific rules remain missing. No claim of official UNC endorsement.

## v2.3 — Single runtime audit and cohort-aware General Education

The `roadmap_audit` runtime now uses `authoritative_audit.audit_roadmap_policy`, which composes the source-backed provisional UNC audit and `cohort_gen_ed` routing. The old `degree_policy.Policy.max_shared_program_courses` cannot be used to approve a roadmap, even if a caller sets its status to `reviewed`. It remains in the repository **only for backwards-compatible legacy tests and storage parsing**, not for current roadmap validation. The legacy trusted-policy schema must be migrated before production; SHA-256 hashes do not constitute independent review.

The 2026–27 IDEAs curriculum requirement inventory is now recorded as categories (first-year foundations, nine distinct Focus Capacities, lab, reflection/integration, campus life, distribution, and conditional B.A. supplemental requirements). It is **not** an approved course-attribute map. Cohorts before Fall 2026 require archived rules; pre-Fall 2022 cohorts may use Making Connections. The current router intentionally blocks those cohorts until archived policies are loaded. Transfers and special exemptions need additional review.

**Remaining gaps:** verified course attribute lists and approved exemptions, cross-listed equivalencies, 2026–27 policies for every program, course availability, professional-school exceptions, full General Education assignment optimizer, independent review, and real-degree eligibility. The legacy policy module is not safe for production and should be deleted after migrating the old store/tests. The application remains a demonstration only.

Source: https://catalog.unc.edu/undergraduate/ideas-in-action/ (2026–2027), https://catalog.unc.edu/undergraduate/degree-requirements/.

## v2.4 — Full-catalog discovery workflow and per-program blockers

The product target remains **all UNC undergraduate majors and minors**. The bundled data is **not** a full verified UNC catalog, and **no graduation planning has been unlocked**. An academic advisor or authorized reviewer must independently verify requirements and planner enforcement before release.

### Import the official index

When the official site is reachable on your computer, run:

```bash
python -m src.official_index_import --fetch --output data/unc_program_registry.json
```

Alternatively, save the complete official index HTML and run:

```bash
python -m src.official_index_import --html saved_unc_index.html --output data/unc_program_registry.json
```

The importer rejects partial pages containing fewer than 100 programs by default, fingerprints the source, and marks every discovered program **unreviewed**. Discovery never establishes planning eligibility. Do not change the minimum to bypass an incomplete import in production.

### Coverage and API

Start `python server.py`. `GET /api/coverage-detail` lists each discovered program, its source availability, and missing verification artifacts. `POST /api/degree-plan` accepts selected program IDs and returns HTTP 422 with specific blockers rather than inventing a schedule. The existing six-course Math prototype is separate and cannot certify graduation.

### Accuracy and security notes

The catalog index HTML could not be downloaded in this environment because DNS resolution failed. No all-program requirements database or verified course-attribute inventory is bundled. The coverage ledger intentionally ignores `plan_ready`, `reviewer`, and similar fields supplied in discovery files: those fields cannot grant authority. A future trusted verification service must bind reviewed evidence to an immutable catalog version, enforce source and reviewer authentication, and run full degree-wide constraints. The current system is not an official UNC advising service.

Run `python -m unittest discover -s tests -q` to verify all 179 tests.


## v2.5: Offline university-wide evidence batch

This milestone adds `src.catalog_batch` for deterministic, fail-closed ingestion of **saved** official 2026–2027 program pages. It validates the registry URL and filename for each program, checks catalog-year and visible requirement indicators, fingerprints source bytes, emits a program-by-program manifest, and never marks pages as academically verified.

Run after importing the official index:

```bash
python -m src.catalog_batch --registry data/unc_program_registry.json --sources saved_program_pages --output imported_program_pages --allow-partial
```

Omit `--allow-partial` to require a candidate page for **every** registered program. A candidate is only source evidence: it is not a machine-readable or reviewed degree requirement. Downloading source pages is a separate step and is not silently simulated. The complete 2026–2027 UNC index and source pages have not been imported in this environment. No degree-planning certification is enabled.

## Version 2.6 — source snapshot integrity and stale evidence protection

This release adds `src/catalog_snapshot_integrity.py`, which independently verifies the imported evidence manifest against the bytes of each candidate HTML page. It rejects missing, modified, duplicate, unsafe-ID, and unmanifested HTML evidence. Run from the project root:

```bash
python -c "from src.catalog_snapshot_integrity import verify_snapshot; print(verify_snapshot('saved_program_pages', require_complete=True))"
```

Run this **only after** importing a real full source batch; the directory is not prepopulated. `catalog_batch.batch_import` now refuses to reuse a destination containing stale HTML pages from previous imports. Use a fresh output directory for each import.

**Important:** Integrity verification proves only that local source bytes match the manifest. It does **not** prove that a page is an authentic live UNC page, that its rules were parsed correctly, or that any degree has been reviewed or approved. The local environment could not reach the UNC website; no complete catalog dataset has been collected in this release. The real graduation endpoint remains blocked.


## v2.7 release integrity audit

Run `python -m src.release_audit --registry data/unc_program_registry.json --snapshot saved_program_pages --output coverage_report.json` after importing an official UNC index and program HTML evidence. The command exits nonzero when evidence is absent, malformed, or inconsistent. `GET /api/release-audit` exposes the same fail-closed coverage information. This **does not** approve any program.

**Blocking dependency:** A complete university-wide catalog cannot be populated from this build environment because its DNS/network access to catalog.unc.edu is unavailable. Do not imply every UNC program is supported. Obtain the official catalog snapshot in a network-enabled environment, then independently review each program and test real student records before enabling complete-degree planning.

## v2.8 — Source-linked requirement-row extraction

The new `src.requirement_evidence` module extracts course-code-bearing rows from actual, saved program catalog HTML **after** the batch snapshot passes its integrity checks. Each candidate retains the source URL, source SHA-256, table/row coordinates, original cells, and ambiguity flag. No extracted row is considered a verified academic requirement, and no degree-plan endpoint is enabled.

After obtaining a complete official registry and an evidence snapshot using the earlier documented import commands, run:

```bash
python -m src.requirement_evidence --registry data/unc_program_registry.json --snapshot saved_evidence --output data/requirement_review_queue.json
python -m unittest discover -s tests -q
```

The local execution environment still cannot resolve `catalog.unc.edu`, so **no university-wide live import or independent review has been completed**. This is a functional offline evidence-extraction milestone, not completion of university-wide verified coverage. HTML tables may include examples, electives, notes, or unrelated sections; all extracted rows need contextual human review.

## v2.9 — Evidence extraction correctness and input hardening

- Fixed HTML table parsing for inline tags, nested tables, and hidden template elements.
- Candidate rows **always** require human interpretation. `ambiguity_detected` is a heuristic only and does not grant approval.
- Rejects empty source files and malformed/unhashable program IDs with validation errors.
- Regression tests cover all of the above.

**Data limitation:** This distribution still does not include the complete official 2026–2027 program catalog, reviewed program rules, verified course attributes, or a validated degree-completion solver. The graduation-planning API remains blocked. A passing automated test suite does not establish academic correctness or independent verification. Students should consult UNC advisors and Tar Heel Tracker for official progress.
