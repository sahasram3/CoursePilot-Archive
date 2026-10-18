"""Verify that a local catalog evidence store matches its manifest.

This verifies byte integrity and batch consistency, NOT academic correctness.
"""
import hashlib
import json
import re
from pathlib import Path

SAFE_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,119}\Z')


def verify_snapshot(directory, *, require_complete=False):
    directory = Path(directory)
    manifest = json.loads((directory / 'batch_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('catalog_year') != '2026-2027':
        raise ValueError('Unexpected catalog year')
    records = manifest.get('records')
    if not isinstance(records, list) or not records or manifest.get('total_programs') != len(records):
        raise ValueError('Manifest program count mismatch')
    ids = set()
    errors = []
    candidate_ids = set()
    for record in records:
        pid = record.get('id')
        if not isinstance(pid, str) or not SAFE_ID.fullmatch(pid) or pid in ids:
            raise ValueError('Unsafe or duplicate manifest program id')
        ids.add(pid)
        if record.get('status') == 'candidate':
            candidate_ids.add(pid)
            path = directory / (pid + '.html')
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record.get('sha256'):
                errors.append('Missing or modified evidence: ' + pid)
    stored = {p.stem for p in directory.glob('*.html')}
    for stale in sorted(stored - candidate_ids):
        errors.append('Stale or unmanifested evidence: ' + stale)
    if require_complete and len(candidate_ids) != len(records):
        errors.append('Incomplete catalog evidence batch')
    if errors:
        raise ValueError('; '.join(errors))
    return {'catalog_year': manifest['catalog_year'], 'programs': len(records),
            'candidate_pages': len(candidate_ids), 'verified_academic_rules': 0,
            'status': 'source_integrity_only'}
