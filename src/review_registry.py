"""Human review workflow for UNC program and course evidence.

Evidence can be staged, but cannot be promoted by a parser or an LLM.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse
import json

CATALOG='2026-2027'
DOMAIN='catalog.unc.edu'

@dataclass(frozen=True)
class Evidence:
    id: str
    program: str
    claim: str
    source_url: str
    excerpt: str
    catalog_year: str
    status: str = 'needs_review'
    reviewer: str = ''
    reviewed_utc: str = ''
    source_sha256: str = ''


def stage(id, program, claim, source_url, excerpt, catalog_year=CATALOG):
    host=urlparse(source_url).hostname
    if host != DOMAIN or not source_url.startswith('https://'):
        raise ValueError('Only official HTTPS UNC catalog sources accepted')
    if not excerpt.strip() or not claim.strip():
        raise ValueError('Source excerpt and claim required')
    return Evidence(id,program,claim,source_url,excerpt,catalog_year,
                    source_sha256=sha256(excerpt.encode()).hexdigest())


def approve(evidence, reviewer, verified_catalog_year, source_checked):
    if not source_checked or not reviewer.strip():
        raise ValueError('Human source verification and reviewer required')
    if verified_catalog_year != evidence.catalog_year:
        raise ValueError('Catalog edition mismatch: do not approve')
    if evidence.status != 'needs_review':
        raise ValueError('Evidence is not awaiting review')
    return Evidence(**{**asdict(evidence),'status':'human_verified',
                       'reviewer':reviewer.strip(),
                       'reviewed_utc':datetime.now(timezone.utc).isoformat()})


def can_schedule(evidence):
    return bool(evidence and evidence.status=='human_verified' and evidence.reviewer
                and evidence.reviewed_utc and evidence.catalog_year==CATALOG)


def export(records,path):
    with open(path,'w',encoding='utf-8') as f:
        json.dump({'catalog_year':CATALOG,'records':[asdict(r) for r in records]},f,indent=2)
