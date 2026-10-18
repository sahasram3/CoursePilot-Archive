"""Cohort-specific General Education evidence router, never a degree certifier.

Catalog publication year is NOT interchangeable with a student's entry cohort.
Unknown cohorts and course attributes must never silently satisfy requirements.
"""
from dataclasses import dataclass
from datetime import date

IDEAS_URL = 'https://catalog.unc.edu/undergraduate/ideas-in-action/'

@dataclass(frozen=True)
class GenEdRouting:
    cohort: str | None
    curriculum: str | None
    catalog_year: str | None
    approved_for_planning: bool
    blockers: tuple[str, ...]
    evidence_url: str = IDEAS_URL


def route_gen_ed(*, entering_term=None, catalog_year='2026-2027', transfer=False,
                 exception_reviewed=False):
    """Only route cohorts; no inferred course satisfaction or waiver.

    The 2026-27 IDEAs catalog expressly applies to Fall 2026 entrants.
    Older cohorts require their own archived, verified rules. Transfers and
    exceptions require a separate determination even when entry term matches.
    """
    if not isinstance(entering_term, str) or not entering_term.strip():
        return GenEdRouting(None, None, None, False, ('entering_cohort_missing',))
    if catalog_year != '2026-2027':
        return GenEdRouting(entering_term, None, None, False, ('catalog_year_unsupported',))
    if entering_term != 'Fall 2026':
        return GenEdRouting(entering_term, None, None, False,
                            ('archived_cohort_requirements_needed',))
    blockers=['ideas_course_attributes_not_verified',
              'ideas_full_requirement_structure_not_reviewed']
    if transfer and not exception_reviewed:
        blockers.append('transfer_gen_ed_applicability_requires_review')
    return GenEdRouting(entering_term,'IDEAs in Action','2026-2027',False,tuple(blockers))


def audit_gen_ed(*, entering_term=None, catalog_year='2026-2027',
                 course_attributes=None, transfer=False):
    routing=route_gen_ed(entering_term=entering_term,catalog_year=catalog_year,transfer=transfer)
    blockers=list(routing.blockers)
    if course_attributes is None:
        blockers.append('verified_course_gen_ed_attributes_missing')
    else:
        # Caller-supplied attributes are untrusted; cannot authorize a pass.
        blockers.append('course_attributes_require_trusted_catalog_provenance')
    return {'eligible':False,'degree_certified':False,'curriculum':routing.curriculum,
            'cohort':routing.cohort,'blockers':sorted(set(blockers)),
            'source_url':routing.evidence_url}

# Direct transcription of requirement categories from the official 2026-27
# IDEAs table. This is a REQUIREMENT INVENTORY, not a list of approved courses.
# The course-to-attribute mapping, exemptions, overlapping rules and transfer
# equivalencies still require a trusted catalog dataset and human review.
IDEAS_2026_REQUIREMENTS = {
    'first_year': ('IDST 101','IDST 111L','first_year_seminar_or_launch',
                   'ENGL 105','global_language_through_level_3'),
    'focus_capacities': ('aesthetic_interpretive','creative_expression',
                         'human_past','ethical_civic','global_engagement',
                         'natural_science','power_society','quantitative_reasoning',
                         'ways_of_knowing'),
    'focus_lab': ('empirical_investigation_lab',),
    'reflection_integration': ('research_discovery',
        'high_impact_or_second_research','communication_beyond_carolina',
        'interdisciplinary','lifetime_fitness','campus_life_8_events_4_categories'),
    'additional': ('foundations_american_democracy','disciplinary_distribution_3',
                   'ba_supplemental_gen_ed_if_applicable'),
}

IDEAS_2026_CONSTRAINTS = {
    'focus_capacities_distinct_courses': 9,
    'exam_credit_focus_capacity_max': 5,
    'campus_life_events': 8,
    'campus_life_categories': 4,
    'no_focus_capacity_and_ba_supplemental_double_count': True,
    'no_research_and_high_impact_same_course': True,
    'first_year_foundations_deadline': 'first_two_semesters_except_global_language',
    'course_approved_attributes_required': True,
    'source_url': IDEAS_URL,
}
