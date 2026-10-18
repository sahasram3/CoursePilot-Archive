"""Server-owned authorization boundary for complete degree planning.

No client-provided approval, policy, or course data is trusted. Until every
required reviewed artifact is installed, real degree planning is unavailable.
"""
from .catalog_registry import validate_selection
from .planning_eligibility import evaluate_combination
from .trusted_policy_store import load_policy, TrustError


def check_degree_plan_request(selections, *, registry, reviews, checklists,
                              trusted_policy_directory, manifest_pin=None,
                              course_rules=None, expanded_courses=None,
                              compatibility_attestation=None):
    # Selection is the ONLY student-controlled academic input to this gate.
    validate_selection(selections,registry)
    blockers=[]
    try:
        policy=load_policy(trusted_policy_directory,'unc-undergrad',pinned_manifest_sha256=manifest_pin)
    except TrustError:
        policy=None
        blockers.append('trusted_university_policy_unavailable')
    result=evaluate_combination(selections,registry,reviews,checklists,
                                course_rules=course_rules,
                                expanded_courses=expanded_courses,
                                compatibility_attestation=compatibility_attestation)
    blockers.extend(result['blockers'])
    # Even when all records pass, final degree solver and catalog-wide checks
    # are not yet complete. Do not open this gate based on a boolean flag.
    blockers.append('complete_degree_solver_not_validated')
    return {'eligible':False,'blockers':sorted(set(blockers)),
            'degree_certified':False,'policy_loaded':policy is not None,
            'notice':'Real UNC degree planning remains disabled until complete validated constraints and trusted catalog coverage are available.'}
