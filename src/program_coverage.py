"""University-wide UNC program registry and explicit coverage reporting.

Program discovery uses the official index; no hardcoded Math-only program list.
Never conflate discovered program names with audited/plan-ready programs.
"""
import json
from pathlib import Path
from .catalog import discover, INDEX
CATALOG='2026-2027'

def registry_from_index(html):
    items=discover(html)
    return {'catalog_year':CATALOG,'source_url':INDEX,'total_discovered':len(items),
            'programs':[{'id':p['url'].rstrip('/').split('/')[-1], 'name':p['name'],
                         'kind':p['kind'], 'url':p['url'],
                         'discovery_status':'discovered',
                         'requirements_status':'unreviewed',
                         'plan_ready':False} for p in items]}

def coverage(registry, reviewed_ids=(), plan_ready_ids=()):
    all_ids={p['id'] for p in registry['programs']}
    reviewed=set(reviewed_ids)&all_ids; ready=set(plan_ready_ids)&all_ids
    if not ready<=reviewed: raise ValueError('Plan-ready must be reviewed')
    return {'catalog_year':registry['catalog_year'], 'discovered':len(all_ids),
            'reviewed':len(reviewed),'plan_ready':len(ready),
            'unreviewed':len(all_ids-reviewed),'not_plan_ready':len(all_ids-ready),
            'unmatched_reviewed_ids':sorted(set(reviewed_ids)-all_ids)}

def save_registry(html,path):
    registry=registry_from_index(html)
    Path(path).write_text(json.dumps(registry,indent=2,ensure_ascii=False))
    return registry
