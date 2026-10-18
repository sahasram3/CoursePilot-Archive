"""Extract reviewable UNC program requirement rows from saved catalog HTML.

This is an evidence index, NOT an academic rule parser or degree certification.
No candidate is automatically approved, even when a course code is detected.
"""
import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

COURSE = re.compile(r'(?<![A-Za-z0-9])([A-Z]{2,6})\s*([0-9]{3}[A-Z]?)(?![A-Za-z0-9])')
AMBIGUOUS = re.compile(r'\b(or|and/or|choose|select|minimum|maximum|at least|one of|two of|additional|elective|substitut|permission|grade|gpa|prerequisit|corequisit|excluding|except|may count|double.count|concentration|track|hours above)\b',re.I)

class Tables(HTMLParser):
    """Conservative table reader: nested markup is text, nested tables stay separate.

    Do not silently merge nested table rows into outer requirements. These are
    review candidates only, never authoritative course requirements.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.stack = []
        self.skip = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'template'):
            self.skip.append(tag)
            return
        if self.skip:
            return
        if tag == 'table':
            self.stack.append({'rows': [], 'row': None, 'cell': None})
        elif self.stack:
            t = self.stack[-1]
            if tag == 'tr':
                t['row'] = []
            elif tag in ('td', 'th') and t['row'] is not None:
                t['cell'] = []
            elif tag in ('br', 'hr') and t['cell'] is not None:
                t['cell'].append(' ')

    def handle_data(self, data):
        if not self.skip and self.stack and self.stack[-1]['cell'] is not None:
            self.stack[-1]['cell'].append(data)

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if not self.stack:
            return
        t = self.stack[-1]
        if tag in ('td', 'th') and t['cell'] is not None and t['row'] is not None:
            t['row'].append(' '.join(''.join(t['cell']).split()))
            t['cell'] = None
        elif tag == 'tr' and t['row'] is not None:
            if any(t['row']):
                t['rows'].append(t['row'])
            t['row'] = None
            t['cell'] = None
        elif tag == 'table':
            self.tables.append(t['rows'])
            self.stack.pop()

def extract_rows(raw,program_id,source_url):
    if not isinstance(raw, bytes) or not raw or len(raw)>2_000_000:raise ValueError('Invalid source size')
    html=raw.decode('utf-8',errors='strict')
    p=Tables();p.feed(html)
    rows=[]
    for ti,table in enumerate(p.tables):
        for ri,cells in enumerate(table):
            combined=' | '.join(cells)
            matches=sorted(set(f'{m.group(1)} {m.group(2)}' for m in COURSE.finditer(combined)))
            if not matches:continue
            rows.append({'table_index':ti,'row_index':ri,'cells':cells,'course_codes':matches,
                         'needs_interpretation':True, 'ambiguity_detected':bool(AMBIGUOUS.search(combined)),
                         'review_status':'unreviewed','source_sha256':hashlib.sha256(raw).hexdigest()})
    return {'program_id':program_id,'source_url':source_url,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'tables_found':len(p.tables),'candidate_rows':rows,'approved_rules':0,
            'notice':'Every candidate requires human interpretation, including apparently simple rows. No academic requirement or prerequisite is approved.'}

def build_queue(registry_file,snapshot_dir,output_file):
    from .catalog_registry import read_registry
    from .catalog_snapshot_integrity import verify_snapshot
    registry=read_registry(registry_file)
    snapshot_dir=Path(snapshot_dir)
    integrity=verify_snapshot(snapshot_dir,require_complete=False)
    if registry.get('catalog_year')!='2026-2027':raise ValueError('Unexpected catalog year')
    manifest=json.loads((snapshot_dir/'batch_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('total_programs')!=len(registry['programs']):raise ValueError('Snapshot/registry count mismatch')
    expected={p['id']:p['url'] for p in registry['programs']}
    items=[]
    for rec in manifest['records']:
        pid=rec['id']
        if pid not in expected:raise ValueError('Unknown program in manifest')
        if rec['status']!='candidate':continue
        if rec.get('source_url')!=expected[pid]:raise ValueError('Source URL mismatch')
        path=snapshot_dir/(pid+'.html')
        if path.is_symlink():raise ValueError('Symlink evidence forbidden')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=rec['sha256']:raise ValueError('Evidence changed')
        items.append(extract_rows(raw,pid,expected[pid]))
    result={'catalog_year':'2026-2027','programs_with_candidate_evidence':len(items),
            'candidate_rows':sum(len(x['candidate_rows']) for x in items),'approved_rules':0,
            'snapshot_integrity':integrity,'programs':items,
            'notice':'Evidence candidates require independent human interpretation and review; no graduation plans authorized.'}
    dest=Path(output_file);dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');tmp.replace(dest)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--registry',required=True);ap.add_argument('--snapshot',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();r=build_queue(args.registry,args.snapshot,args.output)
    print(json.dumps({k:r[k] for k in ('programs_with_candidate_evidence','candidate_rows','approved_rules')},indent=2))
if __name__=='__main__':main()
