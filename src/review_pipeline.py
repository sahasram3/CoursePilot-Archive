"""Offline-first, fail-closed review pipeline for UNC program pages.

Input: registry JSON and local HTML files named <program-id>.html.
Output: evidence queue with source fingerprints, review flags, and diffs.
Never translates prose into approved requirements automatically.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .catalog_registry import read_registry, write_registry_atomic

YEAR_PATTERN = re.compile(r'2026\s*[–-]\s*2027\s+Academic\s+Catalog', re.I)
KEYWORDS = re.compile(r'prerequisit|corequisit|minimum grade|credit hour|requirements|residen|double.count|concentration|track|elective',re.I)


def extract_evidence(html, program, *, captured_at=None):
    """Extract verbatim page evidence; no automatic academic-rule approval."""
    if not isinstance(html,str) or not html.strip():
        raise ValueError('Empty HTML source')
    url=program['url']
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.netloc!='catalog.unc.edu' or not parsed.path.startswith('/undergraduate/programs-study/'):
        raise ValueError('Only official UNC program URLs are allowed')
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup(['script','style','nav','footer']):tag.decompose()
    heading=soup.find('h1')
    text=soup.get_text(' ',strip=True)
    tables=[]
    for table in soup.select('table'):
        rows=[]
        for tr in table.select('tr'):
            cells=[c.get_text(' ',strip=True) for c in tr.find_all(['th','td'],recursive=False)]
            if cells:rows.append(cells)
        if rows:tables.append(rows)
    headings=[h.get_text(' ',strip=True) for h in soup.select('h2,h3,h4')]
    flags=[]
    if not YEAR_PATTERN.search(text):flags.append('catalog_year_not_confirmed')
    if not tables:flags.append('no_requirement_tables_detected')
    if not heading:flags.append('missing_page_heading')
    if len(text)<250:flags.append('possibly_incomplete_page')
    evidence={
        'id':program['id'],'name':program['name'],'kind':program['kind'],'url':url,
        'source_sha256':hashlib.sha256(html.encode('utf-8')).hexdigest(),
        'captured_at_utc':captured_at or datetime.now(timezone.utc).isoformat(),
        'catalog_year_requested':'2026-2027',
        'catalog_year_visible':bool(YEAR_PATTERN.search(text)),
        'page_heading':heading.get_text(' ',strip=True) if heading else None,
        'section_headings':headings,
        'tables':tables,
        'evidence_excerpt':text[:20000],
        'keyword_hits':sorted({m.group(0).lower() for m in KEYWORDS.finditer(text)}),
        'review_flags':flags,
        'review_status':'needs_human_review',
        'plan_ready':False,
        'rule_records_approved':0,
    }
    return evidence


def build_review_queue(registry, html_directory, previous=None, *, captured_at=None):
    """Produce coverage of *every* registry entry, including missing HTML."""
    directory=Path(html_directory)
    previous_by_id={p['id']:p for p in (previous or {}).get('programs',[])}
    results=[]
    for program in registry['programs']:
        filename=directory/(program['id']+'.html')
        if not filename.is_file():
            results.append({'id':program['id'],'name':program['name'],'kind':program['kind'],
                            'url':program['url'],'review_status':'source_missing',
                            'plan_ready':False,'review_flags':['source_html_not_supplied']})
            continue
        evidence=extract_evidence(filename.read_text(encoding='utf-8'),program,captured_at=captured_at)
        previous_item=previous_by_id.get(program['id'])
        if previous_item and previous_item.get('source_sha256')!=evidence['source_sha256']:
            evidence['review_flags'].append('source_changed_since_last_snapshot')
            evidence['previous_sha256']=previous_item.get('source_sha256')
        results.append(evidence)
    statuses={}
    for p in results:statuses[p['review_status']]=statuses.get(p['review_status'],0)+1
    return {'catalog_year_requested':'2026-2027',
            'index_url':'https://catalog.unc.edu/undergraduate/programs-study/',
            'programs_discovered':len(results), 'sources_supplied':sum('source_sha256' in p for p in results),
            'approved_for_planning':0,'status_counts':statuses,'programs':results,
            'notice':'Evidence is unreviewed. No program is approved for planning.'}


def main():
    ap=argparse.ArgumentParser(description='Build a source-backed, unapproved UNC program review queue.')
    ap.add_argument('--registry',default='data/unc_program_registry.json')
    ap.add_argument('--html-dir',required=True)
    ap.add_argument('--output',default='data/program_review_queue.json')
    ap.add_argument('--previous',help='Previous review queue for source-change detection')
    args=ap.parse_args()
    registry=read_registry(args.registry)
    if not registry['programs']:raise SystemExit('Registry is empty. Import the UNC index first.')
    previous=json.loads(Path(args.previous).read_text(encoding='utf-8')) if args.previous else None
    result=build_review_queue(registry,args.html_dir,previous)
    write_registry_atomic(result,args.output)
    print(json.dumps({k:result[k] for k in ('programs_discovered','sources_supplied','approved_for_planning','status_counts')},indent=2))

if __name__=='__main__':main()
