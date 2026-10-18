# PreReqPath — Product Requirements

## Promise
A UNC-Chapel Hill undergraduate selects 1–2 majors and 0–2 minors (at most three programs), enters completed,
in-progress, AP/IB and transfer credit, chooses a graduation term, and receives a feasible semester-by-semester plan,
or a clear explanation of why none exists plus verified fixes.

## Scope
All undergraduate majors, minors, tracks and concentrations in the official catalog index, unlocked program by
program as each is verified. Catalog years: 2026–2027 now (Fall 2026 entrants). The data model is versioned by
catalog year so archived editions can be added from legitimately obtained copies.

## Accuracy contract
1. Every requirement, course fact and university policy keeps its official source URL, catalog year, verbatim
   source text, and a verification status.
2. Interpretations of ambiguous catalog wording are written down next to the requirement and shown to students.
3. A requirement that can't be interpreted confidently is flagged `uncertain` and never treated as satisfied. The
   plan is still produced, with the gap shown.
4. Verification is pinned to source text; a catalog change downgrades it automatically.
5. No plan is ever labeled graduation-certified; plans are "provisional".
6. Assumptions a plan depends on (unknown grades, placement, offering terms) are shown on the affected course.

## Status
- **v1.0 (MVP):** full course catalog, program index and AP/IB tables; requisite and program parsers; two-stage
  CP-SAT planner with explanations and one-click fixes; verified Mathematics B.A. and Economics B.A., including the
  double major; React app with prerequisite map; Docker and Render deployment. 83 backend tests and 15 browser checks.
- **Next:** generic parsing of all program pages with coverage scores; verify CS B.S., BSBA, Biology B.S. and
  Psychology B.A.; minors; Gen Ed assignment from course attributes; offering history; saved plans.
