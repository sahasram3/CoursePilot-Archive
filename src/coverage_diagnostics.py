"""Conservative, actionable coverage ledger for all discovered UNC programs.

Discovery is not academic-rule verification. Student input cannot alter status.
"""
from pathlib import Path
import json

REQUIRED_ARTIFACTS = ('program_requirements', 'course_prerequisites', 'course_credits',
                      'gen_ed_attributes', 'degree_wide_policies', 'term_offerings',
                      'program_restrictions', 'review_attestation')


def diagnostics(registry, evidence_dir=None):
    if registry.get('catalog_year') != '2026-2027':
        raise ValueError('Catalog year mismatch')
    programs=registry.get('programs')
    if not isinstance(programs,list):
        raise ValueError('Invalid program registry')
    seen=set(); result=[]
    base=Path(evidence_dir) if evidence_dir is not None else None
    for program in programs:
        pid=program.get('id')
        if not isinstance(pid,str) or not pid or pid in seen or '/' in pid or '\\' in pid or pid in ('.','..'):
            raise ValueError('Invalid or duplicate program identifier')
        seen.add(pid)
        if program.get('kind') not in ('major','minor'):
            raise ValueError('Invalid program kind')
        has_source=bool(base and (base/(pid+'.html')).is_file())
        # Source availability is NOT a proxy for verified requirements.
        result.append({'id':pid,'name':program['name'],'kind':program['kind'],
                       'catalog_source':program.get('url'),
                       'source_snapshot_available':has_source,
                       'requirements_verified':False,'plan_ready':False,
                       'missing_artifacts':list(REQUIRED_ARTIFACTS),
                       'next_action':'Review official program page and all course descriptions' if has_source else 'Import official catalog source HTML'})
    return {'catalog_year':'2026-2027','discovered':len(result),
            'verified':0,'plan_ready':0,'programs':result,
            'warning':'This ledger intentionally does not trust plan_ready or approval flags in an imported registry.'}


def for_selection(registry, selections, evidence_dir=None):
    from .catalog_registry import validate_selection
    validate_selection(selections,registry)
    ledger=diagnostics(registry,evidence_dir)
    lookup={p['id']:p for p in ledger['programs']}
    return {'eligible':False,'degree_certified':False,
            'programs':[lookup[p['id']] for p in selections],
            'blockers':['no_verified_complete_program_dataset','complete_degree_solver_not_validated'],
            'notice':'A roadmap is not available for this combination. No graduation requirements were invented.'}
