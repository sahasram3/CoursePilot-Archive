# CoursePilot
## Product Requirements Document

**Product Owner:** Sahasra M. | Founder & Product Developer  
**Version:** 1.0  
**Date:** October 2026  
**Stage:** MVP Validation  
**Repository:** [CoursePilot on GitHub](https://github.com/sahasram3/CoursePilot)

---

## 1. Executive Summary

CoursePilot is a degree-planning platform that helps UNC–Chapel Hill undergraduates translate complex academic requirements into actionable, semester-by-semester graduation plans.

Students currently navigate degree requirements, course prerequisites, academic policies, and credit restrictions across multiple resources. Understanding whether a particular combination of majors and minors is feasible often requires manually piecing together information and anticipating how individual course decisions affect future semesters.

CoursePilot addresses this problem through a constraint-based planning engine that evaluates academic requirements alongside a student's completed coursework, incoming credits, and target graduation date.

Rather than simply recommending courses, CoursePilot aims to answer a more consequential question:

**"Given what I've already completed and what I want to study, what is a feasible path to graduation?"**

The initial MVP focuses on Mathematics B.A. and Economics B.A., including their double-major combination. This intentionally narrow scope allows the core planning experience and academic rules to be validated before expanding to additional programs.

**Product principle:** Academic accuracy and student trust take priority over breadth of coverage.

---

## 2. Problem Definition

### The problem

University degree requirements are designed to communicate what students must complete, but they do not automatically translate those requirements into personalized schedules.

Students must account for several interconnected constraints:

- Major and minor requirements, including elective categories and minimum credit thresholds
- Course prerequisites and prerequisite chains
- Completed, in-progress, AP/IB, and transfer coursework
- Semester credit limits and graduation deadlines
- Potential overlap between multiple academic programs
- Catalog-year requirements and university academic policies

A single decision, such as delaying a prerequisite or adding a second major, can change the feasibility of an entire graduation plan.

### Why existing workflows are insufficient

Official academic catalogs provide authoritative requirements, but students still need to interpret and sequence those requirements.

Degree-audit systems help identify completed and outstanding requirements, but identifying remaining requirements is different from constructing a feasible, balanced multi-semester schedule.

Students need a tool that connects **what remains to be completed** with **when and how those requirements can be completed**.

### Problem hypothesis

Students who are considering academic program changes or navigating multiple sets of requirements would benefit from a planning tool that automatically evaluates constraints and explains the reasoning behind a proposed schedule.

This hypothesis requires validation through student interviews and usability testing; it is not presented as an established research finding.

---

## 3. Target Users

### Primary users

UNC–Chapel Hill undergraduates who:

- Need to plan remaining coursework through graduation
- Are considering switching or adding a major
- Want to understand whether a double-major combination is feasible
- Have completed courses or incoming credits that affect their remaining requirements
- Need to evaluate the implications of a target graduation date

The initial supported audience is limited to students planning Mathematics B.A., Economics B.A., or their double-major combination.

### Secondary users and future audiences

- Students pursuing combinations of majors and minors beyond the initial supported programs
- Transfer students with complex credit equivalencies
- Academic advisors reviewing student-generated provisional plans
- Students evaluating alternative academic pathways before formally declaring a program

### Core job to be done

**When** I am planning my academic path or considering changing my programs,  
**I want** to generate a feasible schedule based on my existing credits, program requirements, and graduation timeline,  
**so that** I can understand my options and make informed decisions before registration.

---

## 4. Product Vision and Strategy

### Long-term vision

Become a trusted academic planning layer that helps students explore degree combinations, evaluate tradeoffs, and understand their path to graduation.

The long-term product is intended to support UNC undergraduate majors, minors, tracks, and concentrations, with program-specific academic rules validated before being enabled for planning.

### MVP strategy

**Depth before breadth.**

Supporting hundreds of programs without sufficiently validated requirements would introduce substantial academic risk.

Instead, CoursePilot begins with a small set of modeled programs and a reusable scheduling engine. This approach prioritizes:

1. A complete end-to-end planning workflow
2. Correct handling of modeled academic constraints
3. Clear explanations of feasible and infeasible plans
4. A user experience that makes complex information understandable
5. An architecture that supports gradual expansion without sacrificing reliability

### Product differentiation

CoursePilot is designed to combine three capabilities:

**Personalization:** Plans account for a student's academic history and goals rather than presenting generic sample schedules.

**Constraint-based optimization:** Course sequencing is evaluated against explicit rules instead of relying solely on language-model-generated recommendations.

**Explainability:** Students can understand the assumptions, limitations, and requirements behind their proposed plans.

---

## 5. MVP Scope

### Supported initial programs

- Mathematics B.A.
- Economics B.A.
- Mathematics B.A. + Economics B.A. double-major combination

These are the initial modeled pathways. Support is considered release-ready only after the relevant requirements and end-to-end planning flows have been validated.

### In scope

- Academic program selection
- Student academic profile and graduation timeline inputs
- Completed and in-progress course entry
- AP/IB and transfer-credit inputs where equivalencies are modeled
- Prerequisite-aware course sequencing
- Semester credit-load constraints
- Constraint-based schedule generation
- Identification of infeasible schedules
- Explanations of modeled academic requirements and blockers
- Regeneration after changing planning inputs
- Responsive web interface
- Explicit identification of provisional assumptions and unsupported requirements

### Out of scope for the initial release

- Full planning support for every UNC major and minor
- Official graduation certification
- Guaranteed course availability or registration seats
- Direct integration with university registration systems
- Automatic verification of institutional transcripts
- Advisor approval or replacement
- Complete General Education allocation unless explicitly modeled
- Unverified interpretation of ambiguous catalog policies

### Scope decision

A program appearing in CoursePilot's searchable catalog does **not** automatically mean the program is supported by the planning engine.

Programs should be distinguished by their actual level of modeling and validation.

---

## 6. User Experience and Core Workflow

### Step 1: Define academic goals

The student selects a supported academic program or combination, indicates their current academic standing, and chooses a target graduation term.

### Step 2: Enter academic history

The student provides completed and in-progress coursework and applicable incoming credits.

The system uses this information to determine which modeled requirements remain outstanding.

### Step 3: Generate a plan

The planning engine evaluates remaining requirements, prerequisite relationships, available semesters, and credit-load constraints.

It produces a semester-by-semester schedule when a feasible solution can be identified under the modeled assumptions.

### Step 4: Review the result

The student sees:

- Courses grouped by semester
- Total credit hours per term
- Requirement coverage where supported
- Relevant prerequisite relationships
- Academic assumptions and unresolved requirements
- Warnings about limitations such as unverified course offerings

### Step 5: Understand blockers

If no feasible schedule exists under the selected constraints, the product should explain why rather than inventing a valid-looking plan.

Examples include insufficient remaining semesters, conflicting prerequisites, or credit-load restrictions.

### Step 6: Explore alternatives

Students can adjust their inputs, such as graduation timing or completed coursework, and generate a revised plan.

The product should make it clear that different inputs can produce different valid schedules.

---

## 7. Functional Requirements

Priority definitions:

- **P0:** Required for a reliable core planning experience
- **P1:** Important improvement following core validation
- **P2:** Longer-term expansion

| ID | Priority | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-01 | P0 | Program selection | Students can select modeled programs; unsupported programs are clearly identified. |
| FR-02 | P0 | Academic history | Students can enter completed and in-progress courses without counting the same course twice. |
| FR-03 | P0 | Incoming credit | Supported AP/IB and transfer equivalencies can be incorporated into remaining requirements. |
| FR-04 | P0 | Prerequisite validation | Generated schedules respect modeled prerequisite relationships and sequencing constraints. |
| FR-05 | P0 | Semester planning | Plans organize courses by semester and display credit totals within configured limits. |
| FR-06 | P0 | Requirement coverage | The system evaluates outstanding requirements against the selected program's modeled rules. |
| FR-07 | P0 | Infeasibility detection | Unsatisfiable inputs produce a clear explanation rather than an incorrectly labeled valid plan. |
| FR-08 | P0 | Academic transparency | The interface communicates provisional status, assumptions, and unsupported academic rules. |
| FR-09 | P0 | End-to-end usability | Students can complete the planning flow through a working public web interface. |
| FR-10 | P1 | Plan regeneration | Students can change relevant inputs and generate an updated schedule. |
| FR-11 | P1 | Alternative plans | Students can explore different feasible schedules or planning tradeoffs. |
| FR-12 | P1 | Requirement explanations | Students can inspect why a course is recommended and which requirement it fulfills. |
| FR-13 | P2 | Additional programs | New majors and minors can be enabled after their rules pass the validation process. |
| FR-14 | P2 | Course availability | Verified historical offering information can inform semester placement. |
| FR-15 | P2 | Saved plans | Students can save and revisit academic plans. |

These requirements define the intended product behavior. They do not imply that every requirement has passed release validation.

---

## 8. Academic Accuracy and Trust

Because CoursePilot influences academic planning decisions, incorrect outputs could cause students to misunderstand their graduation requirements.

Academic reliability is therefore a core product requirement rather than a secondary technical consideration.

### Accuracy contract

1. **Source traceability:** Academic requirements and course facts should retain their official source URL, catalog year, source text, and verification status.

2. **Explicit interpretation:** Ambiguous catalog language must be documented rather than silently interpreted as a definitive rule.

3. **Uncertainty handling:** Requirements that cannot be interpreted confidently must be marked uncertain. They cannot be treated as verified or automatically satisfied.

4. **Catalog versioning:** Requirements must be associated with the applicable catalog edition. A change in source material should trigger revalidation of affected rules.

5. **Provisional outputs:** Generated schedules must never be described as certified graduation plans or official degree audits.

6. **Visible assumptions:** Any unresolved assumptions about grades, placement, equivalencies, or course offerings should be communicated to the student.

7. **Fail-safe behavior:** When the engine cannot establish feasibility under the modeled rules, it must not fabricate a feasible result.

### Program validation model

Each academic program should move through a defined progression:

**Discovered → Parsed → Modeled → Tested → Reviewed → Enabled**

- **Discovered:** The program exists in the official catalog index.
- **Parsed:** Relevant requirements have been extracted into structured data.
- **Modeled:** Requirements have been translated into machine-readable constraints.
- **Tested:** Automated checks cover representative valid and invalid academic scenarios.
- **Reviewed:** Academic rules and edge cases have been checked against authoritative sources.
- **Enabled:** The program is available for student-facing plan generation.

This distinction prevents catalog coverage from being confused with validated planning support.

### Student-facing disclaimer

CoursePilot provides provisional academic plans based on modeled catalog requirements and user-supplied information. Students should verify course availability, degree requirements, and graduation eligibility with official university resources and academic advisors.

---

## 9. Technical Architecture

### Core components

**Frontend:** React and TypeScript for the interactive planning experience.

**Backend:** Python and FastAPI for request handling, academic rule processing, and communication with the optimization engine.

**Optimization:** Google OR-Tools CP-SAT for evaluating course scheduling constraints.

**Academic data:** Structured course and program information derived from UNC catalog resources.

**Deployment:** Docker-based application configuration with Render hosting.

### Why constraint-based optimization?

Course planning is fundamentally a constraint-satisfaction problem.

A generated plan must satisfy multiple interacting conditions, including course sequencing, requirement coverage, semester capacity, and graduation timing.

A constraint solver provides a systematic method for evaluating those conditions and identifying when a feasible solution does not exist.

This approach is preferable to generating schedules solely through unconstrained text prediction because it allows supported academic rules to be expressed and checked explicitly.

However, **a mathematically feasible schedule is not necessarily an academically valid graduation plan** if the underlying catalog model is incomplete.

The reliability of the product therefore depends on both the optimization engine and the accuracy of its source requirements.

### Technical considerations

- Validate inputs before invoking the solver.
- Prevent invalid prerequisite sequences.
- Avoid duplicate course-credit allocation where prohibited.
- Handle solver timeouts and infeasible cases.
- Separate academic source data from interpreted planning rules.
- Maintain automated regression tests.
- Keep deployment configuration reproducible.
- Avoid exposing secrets or sensitive student information.
- Design the interface to communicate loading, error, and unsupported states clearly.

---

## 10. Success Metrics

The MVP should be evaluated on whether it helps students complete a useful planning task accurately, not simply on the number of academic programs listed.

### North Star Metric

**Successful, interpretable plans generated for supported-program users.**

A successful plan is one that satisfies modeled constraints, clearly communicates unresolved assumptions, and can be understood by the student.

### Product metrics

| Metric | Initial Target | Measurement |
|---|---|---|
| Planning task completion | ≥80% | Percentage of supported-program testers who generate and interpret a plan without assistance |
| Perceived usefulness | Median ≥4/5 | Post-task student survey |
| Academic rule compliance | 100% of modeled hard constraints in tested scenarios | Automated validation |
| Infeasibility handling | No fabricated feasible plans in tested cases | Negative test scenarios |
| Critical academic discrepancies | Zero unresolved before broader pilot | Issue tracking and catalog review |
| Initial user research | 10–20 students | Interviews and moderated usability tests |

**These are proposed validation targets, not achieved results.**

### Qualitative research questions

- Which aspects of academic planning are most confusing?
- Do students understand why courses appear in particular semesters?
- Which warnings or explanations increase trust?
- How do students prioritize graduation speed, balanced workloads, and flexibility?
- What academic exceptions are not adequately represented by the initial model?
- At what point would students trust CoursePilot enough to use it before meeting with an advisor?

---

## 11. Risks and Mitigations

| Risk | Potential Impact | Mitigation |
|---|---|---|
| Incorrect interpretation of catalog requirements | Misleading academic guidance | Source traceability, review workflow, and uncertainty flags |
| Missing course-offering information | Courses placed in unavailable terms | Explicit availability disclaimer and future schedule integration |
| Complex double-counting rules | Incorrect requirement coverage | Program-specific rule validation and regression tests |
| Transfer or placement exceptions | Incorrect remaining requirements | Explicit equivalency handling and unresolved-assumption warnings |
| Infeasible schedules | Student confusion or false confidence | Explain blockers and never fabricate a valid plan |
| Unsupported program selection | Misleading perception of coverage | Clearly distinguish catalog discovery from planning support |
| Solver performance limitations | Slow or failed planning requests | Timeouts, performance testing, and clear error states |
| Free-hosting cold starts | Poor first-time user experience | Loading indicators, monitoring, and future hosting evaluation |
| Student data privacy | Unnecessary exposure of academic information | Data minimization and transparent handling of user inputs |

---

## 12. Product Roadmap

### R0 — Initial MVP

**Objective:** Deliver a functional, understandable planning experience for a limited set of supported academic programs.

- Model Mathematics B.A. and Economics B.A. requirements
- Support their double-major planning combination
- Implement prerequisite-aware scheduling
- Accept academic history and graduation-timeline inputs
- Explain infeasible planning constraints
- Deliver a responsive web interface
- Validate representative academic scenarios
- Deploy a publicly accessible demonstration

### R1 — Usability and Reliability

**Objective:** Improve the quality of the student experience and reduce academic uncertainty.

- Conduct student interviews and usability testing
- Resolve high-severity academic rule discrepancies
- Improve explanations of course recommendations
- Introduce clearer alternative-plan comparisons
- Improve loading, error, and empty states
- Refine mobile usability
- Establish repeatable validation and release checks

### R2 — Academic Program Expansion

**Objective:** Expand program coverage through a controlled, repeatable verification process.

Potential next programs include Computer Science B.S., Business Administration B.S.B.A., Biology B.S., and Psychology B.A., subject to catalog verification and implementation feasibility.

Additional priorities:

- Minor support
- Elective and concentration rules
- Program overlap and double-counting policies
- Catalog-year and cohort-specific requirements
- Coverage and verification status tracking

### R3 — Campus-Ready Pilot

**Objective:** Prepare CoursePilot for broader student testing.

- Integrate verified General Education requirements
- Improve AP/IB and transfer-credit equivalencies
- Incorporate course-offering information
- Support saved and revisable plans
- Conduct accessibility testing
- Validate academic edge cases with appropriate university resources
- Expand advisor-informed testing

---

## 13. Launch Readiness

The following criteria should be satisfied before CoursePilot is promoted as a reliable public demo.

### Functional validation

- [ ] Mathematics B.A. planning flow passes end-to-end testing.
- [ ] Economics B.A. planning flow passes end-to-end testing.
- [ ] Mathematics/Economics double-major flow passes representative tests.
- [ ] Infeasible inputs produce clear, accurate explanations.
- [ ] Generated plans respect modeled prerequisites and credit limits.
- [ ] Academic limitations and unverified assumptions are visible.

### Product experience

- [ ] A new user can generate a sample plan without developer assistance.
- [ ] Core planning workflows function on desktop and mobile.
- [ ] Loading and error states are understandable.
- [ ] Unsupported academic programs are clearly identified.
- [ ] The interface distinguishes provisional guidance from official academic advising.

### Technical release

- [ ] Public deployment serves the complete application.
- [ ] Frontend and backend communicate successfully.
- [ ] Deployed version matches the intended GitHub commit.
- [ ] Automated test results are recorded for the release.
- [ ] No sensitive credentials are exposed.
- [ ] Screenshots and a concise product demonstration are available.

---

## 14. Current Product Status

CoursePilot is in the MVP validation stage.

The current implementation is centered on Mathematics B.A., Economics B.A., and their double-major combination. The repository includes the course-planning architecture, structured academic data, a React-based interface, and deployment configuration.

Broader program discovery should not be interpreted as verified planning support.

End-to-end deployment, academic correctness, automated test results, and student usability remain subject to final release verification.

The next priority is to validate the complete student experience for the initial supported programs before expanding the academic catalog.

---

## 15. Product Decision Summary

CoursePilot's most important early product decision is to prioritize **trustworthy planning over maximum feature coverage**.

The challenge is not merely generating a schedule. It is generating a schedule that accounts for real academic constraints, communicates uncertainty, and helps students make decisions with greater confidence.

The MVP is designed to test whether a constraint-based planning experience can meaningfully simplify a complex student workflow.

Future expansion will depend on evidence of academic correctness, usability, and repeatable program validation rather than the number of catalog entries the system can display.
