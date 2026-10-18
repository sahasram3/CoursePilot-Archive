# PreReqPath — Product Requirements

## Promise
A UNC-Chapel Hill undergraduate selects 1–2 majors and 0–2 minors (at most three programs),
enters completed and in-progress coursework, chooses a graduation term, and receives a
feasible semester-by-semester plan to graduation, or a clear explanation of why none exists
and what would make one possible.

## Scope
All undergraduate majors, minors, tracks and concentrations in the official catalog index.
Coverage grows program by program; the pipeline is built for every program from the start.
Catalog years: 2026–2027 now (Fall 2026 entrants); the data model is versioned by catalog
year so archived editions can be added from legitimately obtained copies.

## Accuracy contract
1. Every requirement, course fact and university policy keeps its official source URL,
   catalog year, verbatim source text, and a verification status.
2. Interpretations of ambiguous catalog wording are written down next to the requirement.
3. A requirement that cannot be interpreted confidently is flagged `uncertain`. It is never
   treated as satisfied. The plan is still produced, with the gap shown.
4. Verification is pinned to source text; a catalog change downgrades it automatically.
5. No plan is ever labeled graduation-certified; plans are "provisional".
6. Assumptions the plan depends on (unknown grades, placement, offering terms) are shown on
   the affected course.

## Milestones
- **v0.10 (done):** catalog acquisition for all courses and the program index; requisite and
  program parsers; CP-SAT planner with explanations; verified Mathematics B.A.; React app.
- **Next:** generic parsing of all program pages with a per-program coverage report; hand
  verification of Computer Science B.S., Business Administration B.S.B.A., Biology B.S.,
  Psychology B.A. and Economics B.A.; multi-program plans with cross-program exclusivity.
- **Then:** IDEAs in Action Gen Ed assignment from course attributes; term-offering history;
  plan editing and saving; natural-language plan adjustments that translate to solver
  constraints (never inventing requirements).
