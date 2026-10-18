"""Fail-closed evidence inventory for the entire UNC program registry.

Evidence presence is not the same as academic verification. The report never
promotes an imported HTML page to a reviewed or plan-ready program.
"""
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from .catalog_registry import read_registry
from .catalog_snapshot_integrity import verify_snapshot

CATALOG = "2026-2027"
BASE = "https://catalog.unc.edu/undergraduate/programs-study/"

def audit_release(registry_path, snapshot_directory=None):
    registry = read_registry(registry_path)
    programs = registry["programs"]
    errors = []
    if registry.get("catalog_year") != CATALOG:
        errors.append("Wrong catalog edition")
    if not programs:
        errors.append("No complete university-wide index imported")
    if registry.get("total_discovered") != len(programs):
        errors.append("Registry count mismatch")
    ids = set()
    for p in programs:
        pid = p.get("id")
        url = p.get("url", "")
        if not isinstance(pid, str) or not pid or pid in ids:
            errors.append("Duplicate or invalid program ID")
        ids.add(pid)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "catalog.unc.edu" or not parsed.path.startswith("/undergraduate/programs-study/"):
            errors.append("Unexpected program source URL: " + str(pid))
        if p.get("plan_ready") is True or p.get("requirements_status") == "verified":
            errors.append("Untrusted registry claims verification: " + str(pid))
    snapshot = None
    if snapshot_directory is not None:
        try:
            snapshot = verify_snapshot(snapshot_directory, require_complete=False)
        except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
            errors.append("Snapshot integrity failed: " + str(exc))
    else:
        errors.append("No program evidence snapshot supplied")
    return {
        "catalog_year": CATALOG,
        "programs_discovered": len(programs),
        "source_pages_with_integrity_checks": snapshot["candidate_pages"] if snapshot else 0,
        "programs_independently_reviewed": 0,
        "programs_eligible_for_complete_degree_plans": 0,
        "graduation_planning_enabled": False,
        "errors": sorted(set(errors)),
        "status": "blocked" if errors or not programs else "evidence_only",
        "notice": "Evidence integrity is not independent academic review. Complete-degree planning stays disabled."
    }

def main():
    import argparse
    ap=argparse.ArgumentParser(description="Audit real UNC catalog coverage without inventing approvals")
    ap.add_argument("--registry",default="data/unc_program_registry.json")
    ap.add_argument("--snapshot")
    ap.add_argument("--output")
    args=ap.parse_args()
    report=audit_release(args.registry,args.snapshot)
    rendered=json.dumps(report,indent=2)
    if args.output: Path(args.output).write_text(rendered+"\n",encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["status"]=="evidence_only" else 2)

if __name__=="__main__": main()
