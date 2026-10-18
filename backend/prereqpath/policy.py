"""University-wide undergraduate rules, 2026-2027 catalog.

Each rule carries its source and says how the planner uses it:
  "enforced"  - built into the solver as a constraint
  "checked"   - evaluated on the plan and reported (e.g. needs grades we don't know yet)
  "reported"  - shown to the student, not yet modeled
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

DEGREE_REQS = "https://catalog.unc.edu/undergraduate/degree-requirements/"
IDEAS = "https://catalog.unc.edu/undergraduate/ideas-in-action/"
REGISTRATION = "https://catalog.unc.edu/policies-procedures/registration-enrollment-withdrawal/"
VERIFIED_ON = "2026-10-17"


@dataclass(frozen=True)
class Policy:
    id: str
    summary: str
    source_url: str
    source_text: str
    use: str            # enforced | checked | reported
    value: object = None


POLICIES_2026_2027: dict[str, Policy] = {p.id: p for p in [
    Policy("min_total_hours", "At least 120 semester hours", DEGREE_REQS,
           "Students must successfully complete at least 120 semester hours of coursework.", "enforced", 120),
    Policy("min_unc_hours", "At least 45 academic hours from UNC-Chapel Hill courses", DEGREE_REQS,
           "A minimum of 45 academic credit hours must be earned from UNC-Chapel Hill courses.", "checked", 45),
    Policy("max_transfer_hours", "At most 75 transfer hours", DEGREE_REQS,
           "maximum of 75 transfer hours", "checked", 75),
    Policy("min_cumulative_gpa", "Final cumulative GPA of at least 2.000", DEGREE_REQS,
           "at least a 2.000 final cumulative grade point average on all work attempted", "reported", 2.0),
    Policy("ba_subject_cap", "B.A. (College of Arts & Sciences): at most 45 hours in one subject count toward the degree (ENGL 100/105/105I excluded)",
           DEGREE_REQS, "No more than 45 semester hours in any subject, as defined by subject code", "enforced", 45),
    Policy("major_core_half_at_unc", "At least half of major core courses and hours at UNC-Chapel Hill", DEGREE_REQS,
           "must take at least half of their major core requirements (courses and credit hours) at UNC-Chapel Hill", "checked", 0.5),
    Policy("major_core_gpa", "Major core GPA of at least 2.000 (UNC coursework)", DEGREE_REQS,
           "A minimum cumulative GPA of 2.000 in coursework taken at UNC-Chapel Hill in the major core is required.", "reported", 2.0),
    Policy("major_core_be_limit", "At most two by-exam (BE) courses in a major core", DEGREE_REQS,
           "No more than two courses (six to eight credit hours) of BE credit may be used as part of the major core.", "checked", 2),
    Policy("minor_core_unc_hours", "At least nine minor-core hours at UNC-Chapel Hill", DEGREE_REQS,
           "At least nine hours of core requirements in the minor must be completed at UNC-Chapel Hill.", "reported", 9),
    Policy("max_minors", "At most two minors", DEGREE_REQS,
           "A student may have no more than two minors", "enforced", 2),
    Policy("exclusive_core", "More than half of each major/minor core must be exclusive to it", DEGREE_REQS,
           "more than half (not merely half) of the courses and course credit hours taken to satisfy core requirements must be exclusive to that major/minor",
           "reported", 0.5),
    Policy("eight_semesters", "Degree expected within eight Fall/Spring semesters (summers not counted); a ninth needs an approved petition",
           DEGREE_REQS, "First-year students are expected to complete their undergraduate degree in eight semesters.", "checked", 8),
    Policy("term_min_hours", "At least 12 academic hours in a Fall/Spring semester without dean permission", REGISTRATION,
           "Students may not go below the 12-academic-hour minimum without permission of their dean.", "enforced", 12),
    Policy("term_max_hours", "At most 18 academic hours in a Fall/Spring semester without meeting GPA conditions or dean approval",
           REGISTRATION, "Students may not enroll in more than 18 academic hours unless they have earned a 3.000 grade point average in the preceding regular semester and have a cumulative 2.500 grade point average.",
           "enforced", 18),
    Policy("ideas_gen_ed", "IDEAs in Action General Education (Fall 2026 entrants; earlier cohorts use archived editions)", IDEAS,
           "The requirements outlined in this Catalog are specifically for students beginning their studies at Carolina in fall 2026.",
           "reported"),
]}

BA_SUBJECT_CAP_EXEMPT = {"ENGL 100", "ENGL 105", "ENGL 105I"}


def policies(catalog_year: str) -> list[dict]:
    if catalog_year != "2026-2027":
        return []
    return [{**asdict(p), "verified_on": VERIFIED_ON} for p in POLICIES_2026_2027.values()]
