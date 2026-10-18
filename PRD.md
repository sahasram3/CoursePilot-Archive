# PreReqPath AI — v0.7 catalog verification milestone

## User promise
Generate and regenerate full-horizon plans from a student's next semester to graduation, with Fall/Spring and optional Summer, supporting 1–2 majors and 0–2 minors (maximum three programs) where permitted by official rules.

## Accuracy contract
- Academic requirements, credits, prerequisites and catalog applicability come only from checked UNC sources.
- Extracted data starts as `needs_review`; LLMs and crawlers cannot self-certify.
- Each approved rule must have source URL, exact catalog edition, reviewer, review time and preserved evidence.
- Unknown credits, unresolved OR/AND prerequisite rules, incomplete degree requirements, or unsupported overlap rules block a certified plan.
- Course offering and registration availability remain separate from catalog eligibility.

## This milestone
Evidence review registry, three-program UNC review queue, and tests for verification gates.

## Acceptance criteria for next milestone
- Verify one complete UNC program against 2026–2027 primary source, including all elective paths and footnotes.
- Validate course credit and prerequisite facts independently.
- Convert reviewed data to solver rules and pass full-program audit tests.
- Display a precise coverage indicator and prevent claims of verified completion while coverage is incomplete.

## Not yet built
Complete UNC-wide verified data, multi-program exclusivity checks, validated full-degree optimizer, enrollment feeds, AI conversational edits, and production UI.

## v0.8 — First live-catalog 2026–2027 program-core transcription

The Mathematics B.A. program-core requirement table is recorded in `data/math_ba_2026_evidence.json` with a live 2026–2027 source URL. The program-core audit remains explicitly partial: it does not certify graduation, full elective eligibility, prerequisite compliance, Gen Ed, GPA, residency, or term offerings. Full schedule generation for this program remains gated until those rules are resolved.

## v0.9 explicit university-wide coverage contract

- Product coverage is **all undergraduate UNC Chapel Hill majors and minors**, including B.A./B.S. options and listed tracks/concentrations, not only Mathematics.
- The program registry MUST be generated from the complete official 2026–2027 UNC programs index, not a hardcoded list of favorites. Every program receives independent `discovered`, `requirements_reviewed`, and `plan_ready` statuses; only verified programs may produce authoritative plans.
- Prerequisite evidence MUST be tied to official course catalog entries, including OR alternatives, AND conjunctions, minimum grades, placement/permission and corequisites. If the rule is ambiguous, scheduling MUST fail closed rather than invent a requirement.
- v0.9 provides the generalized registry/coverage logic and a 16-course MATH dependency graph, but not a completed catalog-wide crawl or degree-compliant full program plans.
- Exit criteria: registry contains every official index entry for the applicable catalog edition; 100% reviewed requirements and course dependencies for each marked plan-ready program; integration and regression tests on multiple majors/minors; accurate full-horizon plans; and clearly surfaced unsupported cases.

## v1.0 milestone — integrated provisional degree sequencing

Implemented a program-agnostic bridge between reviewed degree-choice groups and an AND/OR prerequisite-aware full-horizon backtracking planner. Handles course grades, explicit placement/permission tokens, locks, credit limits, and alternative sequences. Missing or unreviewed course rules block scheduling. All outputs are labeled provisional; future availability, university-wide degree requirements, wildcard electives, residency, and program overlaps remain unverified. The goal remains **all UNC majors and minors**, not Mathematics alone; catalog-wide verified data coverage is pending.

## v1.1 web demo acceptance boundary

The prototype provides program selection, completed-course input, start/graduation term selection, optional summer, and multiple provisional plans. The interface disables unsupported programs and explicitly disclaims degree certification. University-wide support remains a product requirement, **not an implemented capability**. Future milestones must ingest and verify every UNC undergraduate major and minor and their applicable catalog-year rules.

## v1.2 university-wide registry milestone

- Import all program links from a complete official UNC index HTML page; preserve source URL, kind, catalog edition, and unreviewed status.
- Display imported majors/minors in a university-wide selector. Accept combinations (1 major, 0 minors), (2,0), (1,1), (2,1), (1,2) without implying program-specific eligibility.
- Disallow duplicates, unknown identifiers, and type mismatches. Reject partial imports by default.
- Distinguish **discovered**, **requirements-reviewed**, and **degree-plan-ready** statuses. Never infer complete support from a program listing.
- Next: actual end-to-end catalog acquisition and per-program verification pipeline, complete degree-wide rules, then multi-program optimization.

## v1.3: Source evidence review and university-wide coverage

- A registry entry is never dropped when its program HTML has not been acquired.
- Store per-program official URL, HTML fingerprint, capture time, page heading, requirement tables, text evidence, and review flags.
- Check for an explicit 2026–2027 catalog heading, but do not interpret a match as sufficient academic verification.
- Flag changes between two source snapshots and require renewed review.
- No program becomes plan-ready through automatic extraction; academic rules require source-level review, eligibility checks, and end-to-end validation.
- Scope remains all UNC undergraduate majors and minors, including BA/BS variants and valid combinations. Coverage statistics must distinguish discovered, source-acquired, reviewed, and plan-ready programs.

## v1.4 milestone — unapproved rule candidates

Convert extracted official catalog evidence into traceable review candidates without asserting that text recognition is academic-rule validation. Every candidate must preserve a source fingerprint and table row or text passage locator. Distinguish fixed-credit single-course rows, choice groups, variable credits, and unstructured policy/prerequisite text. Require review of electives, grades, double counting, catalog year, transfer credit, residency and exceptions before approving rules. No automatically generated candidate may be treated as planning-ready. Expand this pipeline across every program in the official registry; Mathematics is not a scope limitation.

## v1.5 human-in-the-loop approval milestone

- Each candidate is linked to the exact program ID, official source URL, 2026–2027 catalog year, and original HTML SHA-256.
- A human reviewer must explicitly provide identity, verbatim supporting evidence, course selection, rule interpretation, and rationale.
- Fail closed for source mismatch, missing catalog year, ungrounded course codes, invalid counts, or repeat approval.
- Source changes invalidate previously approved records and require re-review.
- Export partial rule records with provenance and explicit `degree_plan_ready: false`. A complete-degree review workflow remains a separate milestone.
- Maintain coverage across all UNC programs; never equate program discovery with verified academic planning.

## v1.6 Whole-program coverage and readiness gate

Before a program can be internally reviewed for planning, a named human reviewer must inspect every enumerated source section and attest to required courses, elective groups, tracks/concentrations, prerequisites/corequisites, grade/GPA rules, credit totals, General Education and university-wide requirements, residency, double-counting, transfer/AP/IB equivalencies, admission/progression, course offerings, and miscellaneous catalog notes. Each category must have evidence and explanatory notes, even when the correct finding is not applicable. All candidates must be resolved and at least one rule approved. Catalog edition and source fingerprint must match. Source changes invalidate readiness.

This is a conservative **data review gate only**, not a degree certification or guarantee of solver support. A later milestone must validate rule-type implementation and complete degree-wide constraints before enabling student plans. The goal remains coverage of every UNC undergraduate major and minor; current program coverage is not complete.

## v1.7 acceptance gate — planning eligibility

- Full degree planning must remain disabled unless a program has a current, human-attested whole-program completeness checklist **and** every relevant academic rule is implemented in the planner.
- Unknown or missing prerequisite rules, missing complete course expansion, source changes, and incomplete category review block planning.
- For combined majors/minors, additionally require human-verified program compatibility, overlap/double-counting, and degree-wide requirements. Structural selection validity is not sufficient.
- Student-facing API returns blockers instead of speculative degree plans. Existing six-course Mathematics demonstration must remain labeled as a demo.
- Passing unit tests does not imply a UNC-certified degree audit or verified university-wide coverage.

## v1.8 implementation: degree-wide policy gate

Implement source-reviewed policy models for graduation-credit minima, Gen Ed
selection groups, UNC residency credits, and cross-program course-sharing limits.
A course may count once toward total earned credits even if a reviewed policy
allows it to satisfy multiple requirement categories. Unknown or missing policy
parameters must block approval rather than be inferred. Future minimum-grade
prerequisites must not be guaranteed from a hypothetical future course grade.

Current implementation is a standalone provisional audit component, not yet
wired to the student-facing degree-plan endpoint. Course-credit provenance
must be enforced at the integration boundary. General Education, residency,
and overlap models are deliberately limited and do not encode every UNC rule.


## v1.9 milestone: integrated provisional roadmap audit

Each proposed sequence receives its own degree-wide audit with explicit blockers;
student UI must surface blockers. A plan remains provisional even if a narrow
policy audit passes. Residency earned credits require completed UNC courses;
planned future courses cannot count as already earned. Student-supplied reviewer
flags or policy records cannot activate full degree planning. A full degree-plan
endpoint must remain fail-closed pending trusted 2026–27 UNC policies and reviewed
program coverage for all requested majors/minors.

## v2.0 trust-boundary milestone

Complete degree plans must use immutable, server-controlled catalog, policy, reviewer and compatibility evidence. Student-provided approval fields are never authoritative. The trusted-policy store checks an operator-pinned manifest hash, file integrity, catalog year, source and reviewer provenance, and mandatory policy fields. This is a *technical integrity gate*, not proof of institutional verification. The full-degree endpoint must remain blocked until every academic constraint is encoded and validated; no API flag can override this. Threat-model tests cover missing pins, tampering, traversal, incomplete review, unknown programs and forged student approval. Next: obtain and independently review actual UNC university policies and implement a complete solver with documented capability coverage.

## v2.1 Official-policy ingestion and blockers

Source-backed 2026–2027 university policy facts are stored as a **not-independently-reviewed** artifact, not a trusted planning approval. Official URLs and per-rule evidence are retained. The partial auditor checks minimum 120 credits, 45 eligible UNC credits, cumulative UNC GPA, per-program majority-exclusive core courses **and** credit hours, major-core UNC half requirements, minor-core nine UNC hours, and BA subject caps, subject to evidence and scope caveats. Unknown course provenance, missing core mapping, incomplete General Education, or cohort mismatches block eligibility. A previous global course-overlap cap cannot represent UNC's per-program majority-exclusivity rule; it must be replaced before graduation planning is enabled. The live 2026–2027 IDEAs curriculum applies to Fall 2026 entrants, not automatically to all 2026–2027 students. No independent registrar review or full-program validation has occurred.

## v2.2 accuracy gate

University-wide policy facts must be evaluated alongside every proposed alternative without conflating projected and earned credits. A provisional audit is always blocked if transcript origin, entering cohort, program core mappings, core GPA, or independent policy review is missing. The existing student-facing six-course Mathematics demo is not a complete degree roadmap. The legacy flat shared-course-count limit is unsuitable for UNC policy; production planning must use per-program strictly-majority exclusivity measured in both courses and credits. Future work: independently review official policy data, implement cohort-specific Gen Ed, and eliminate the legacy audit before enabling production planning.

## v2.3 accuracy acceptance gates

- The roadmap runtime MUST NOT use the old `max_shared_program_courses` threshold for UNC certification.
- No student-submitted approval flags, Gen Ed attribute claims, or policy source fields may authorize planning.
- Entry cohort must be independently distinguished from catalog publication year. Fall 2026 uses the 2026–27 IDEAs inventory; earlier cohorts require the appropriate archived edition, with pre-Fall 2022 potentially using Making Connections.
- All nine Focus Capacities require separate eligible courses, with verified overlap restrictions; a category inventory alone does not satisfy a degree requirement.
- Source-backed transcription is not independent academic approval.
- No graduation certification until all program rules, policy exceptions, Gen Ed attributes, and complete schedule constraints are verified and enforced.

## v2.4 coverage-first milestone

**Goal:** all undergraduate majors/minors, not Math-only. **Delivered:** safe import of a complete official index HTML, provenance hash, university-wide per-program evidence blockers, and an explicit non-certifying `/api/degree-plan` response. **Not delivered:** complete catalog import, human-verified rules for every program, full course-to-GenEd mappings, complete degree solver, authenticated approval, or a public deployment.

**Release gate:** zero programs may be marked plan-ready merely because they appear in the index or a file contains a positive review flag. Every program requires independent catalog rule review, prerequisite and offering data, cohort-aware GenEd rules, university-wide credits/residency/overlap enforcement, and transcript-based adversarial validation. Until these exist, return actionable blockers instead of a purported graduation roadmap.


### v2.5 university-wide source ingestion acceptance criteria
- Every discovered program is associated with an official catalog URL and safe source-file name.
- Source pages must be visibly labeled for the selected catalog edition; absence blocks strict batch import.
- Missing pages are explicit; batch manifests are reproducible and hash each imported page.
- Candidate source pages never imply human verification or permission to plan.
- University-wide readiness requires verified requirements, course-level prerequisites and credits, Gen Ed mapping, overlap rules, course offerings, and independent academic review.

## Version 2.6 — source integrity gate

**Acceptance criteria:** Source evidence must be manifest-consistent; any tampering, missing candidate page, unmanifested stale HTML page, duplicate/unsafe identifier, or catalog-year mismatch fails validation. Batch imports cannot silently preserve old evidence when importing a smaller or changed program set. An intact source manifest does not confer academic approval.

**Coverage status:** All-program discovery and full 2026–2027 catalog verification remain incomplete. The student-facing demo is not a certified academic advisor. Source collection, independent policy review, Gen Ed mappings, course offerings, and program-by-program requirements remain outstanding.


## v2.7 scope and launch gates

- Add machine-readable release coverage audit; reject forged approval and mismatched official source domains.
- Tighten demo API input validation; keep degree planning blocked when evidence is missing.
- Require independent academic review, cohort-specific Gen Ed, verified prerequisites and availability, cross-program overlap checks, transcript equivalency validation, and end-to-end graduation scenario testing before real launch.

## v2.8 implementation and release gate

Implemented: provenance-preserving offline extraction of candidate course rows from saved official catalog program pages, with snapshot integrity validation and explicit unreviewed status. The output is a human review queue, not an executable degree rule database. It must never directly authorize course selection or graduation certification.

Unfinished: collect full catalog source pages; validate every course rule, program requirement, Gen Ed attribute and cohort exception; independently review structured interpretations; validate real multi-term plans. Keep full-degree planning blocked until these are complete.

## v2.9 milestone and release blockers

The requirement evidence reader now handles nested and inline HTML conservatively, and no row is automatically interpreted or approved. Program selection rejects malformed IDs. Verified academic data coverage remains a blocking requirement: acquire official catalog snapshots, review all program-specific requirement logic, course credit/prerequisite attributes, IDEAs eligibility and student-cohort policies, and validate the full-degree optimizer against authoritative audits before enabling production plans. These items are **not complete** in v2.9.
