"""Read-only, fail-closed server-side catalog policy store.

The student HTTP API never accepts reviewer/approval/policy records. The store
requires a separately deployed, SHA-256 pinned manifest; no policy is bundled
as approved. File hashes are integrity checks, not authentication or UNC approval.
"""
import hashlib
import json
import re
from pathlib import Path
from .degree_policy import Policy, PolicyError

class TrustError(ValueError):
    pass

_SHA = re.compile(r'^[0-9a-f]{64}$')

def load_policy(store_dir, policy_id, *, pinned_manifest_sha256=None):
    """Load only a deployment-pinned reviewed policy. Never read arbitrary paths."""
    if not isinstance(policy_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', policy_id):
        raise TrustError('Invalid policy identifier')
    if not isinstance(pinned_manifest_sha256, str) or not _SHA.fullmatch(pinned_manifest_sha256):
        raise TrustError('Trusted deployment manifest hash not configured')
    base = Path(store_dir).resolve()
    manifest_path = base / 'manifest.json'
    try:
        manifest_bytes = manifest_path.read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != pinned_manifest_sha256:
            raise TrustError('Policy manifest integrity mismatch')
        manifest = json.loads(manifest_bytes)
        if manifest.get('schema_version') != 1 or manifest.get('catalog_year') != '2026-2027':
            raise TrustError('Unsupported manifest schema or catalog year')
        entry = manifest.get('policies', {}).get(policy_id)
        if not isinstance(entry, dict) or not _SHA.fullmatch(str(entry.get('sha256', ''))):
            raise TrustError('No trusted reviewed policy for requested identifier')
        # Path is derived solely from validated identifier, not from manifest or client.
        data_bytes = (base / 'policies' / (policy_id + '.json')).read_bytes()
        if hashlib.sha256(data_bytes).hexdigest() != entry['sha256']:
            raise TrustError('Policy content integrity mismatch')
        data = json.loads(data_bytes)
        if data.get('id') != policy_id or data.get('catalog_year') != manifest['catalog_year']:
            raise TrustError('Policy identifier or catalog year mismatch')
        if data.get('status') != 'reviewed' or not data.get('source_fingerprint'):
            raise TrustError('Policy has no completed source review')
        if not data.get('reviewed_at') or not data.get('reviewer'):
            raise TrustError('Missing reviewer provenance')
        # Explicitly reject absent academic constraints; don't default to permissive rules.
        if data.get('min_resident_credits') is None or data.get('max_shared_program_courses') is None:
            raise TrustError('Critical degree-wide policy constraint not encoded')
        policy = Policy(catalog_year=data['catalog_year'], source_url=data['source_url'],
                        reviewer=data['reviewer'], min_total_credits=data['min_total_credits'],
                        gen_ed_groups=tuple((g['name'],tuple(g['courses']),g['minimum']) for g in data.get('gen_ed_groups',[])),
                        max_shared_program_courses=data['max_shared_program_courses'],
                        min_resident_credits=data['min_resident_credits'], status='reviewed')
        return policy
    except (OSError, KeyError, TypeError, json.JSONDecodeError, PolicyError) as exc:
        raise TrustError('Policy record missing, malformed, or untrusted') from exc

def policy_availability(store_dir, *, pinned_manifest_sha256=None):
    """Public-facing availability, never expose local policy files or reviewer credentials."""
    if not pinned_manifest_sha256:
        return {'available':False,'reason':'trusted_policy_manifest_not_deployed'}
    try:
        data=(Path(store_dir)/'manifest.json').read_bytes()
        if hashlib.sha256(data).hexdigest()!=pinned_manifest_sha256:
            return {'available':False,'reason':'trusted_policy_manifest_mismatch'}
        return {'available':True,'reason':'manifest_integrity_verified_not_degree_certification'}
    except OSError:
        return {'available':False,'reason':'trusted_policy_manifest_missing'}
