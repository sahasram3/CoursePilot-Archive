"""Fail-closed, offline batch catalog evidence import. Never approves academic rules."""
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from .catalog_registry import read_registry

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
    def handle_endtag(self, tag):
        if tag in ('script','style') and self.skip:self.skip-=1
    def handle_data(self, data):
        if not self.skip:self.parts.append(data)

def assess_page(program, html):
    if not isinstance(html,str) or len(html)<250:
        return ('invalid','Page missing or too short')
    parser=_Text();parser.feed(html)
    text=' '.join(parser.parts)
    text=re.sub(r'\s+',' ',text)
    title=program['name'].split('–')[0].split('—')[0].strip().lower()
    if not ('2026–2027' in text or '2026-2027' in text):
        return ('edition_unconfirmed','2026–2027 catalog edition not visible in source')
    # Program title check is advisory: site headings can differ from index labels.
    if not any(token in text.lower() for token in title.split()[:2]):
        return ('title_mismatch','Program name could not be matched to page text')
    if 'requirements' not in text.lower():
        return ('requirements_unconfirmed','No visible requirements section')
    return ('candidate','Page contains edition and program/requirements indicators; human review required')

def batch_import(registry_path, source_dir, output_dir, *, strict=True):
    registry=read_registry(registry_path)
    if registry.get('catalog_year')!='2026-2027':raise ValueError('Wrong catalog year')
    programs=registry['programs']
    if not programs:raise ValueError('Cannot import with empty program registry')
    source_dir=Path(source_dir);output_dir=Path(output_dir)
    records=[]; payloads={};seen=set()
    for program in programs:
        pid=program.get('id')
        if not isinstance(pid,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,119}',pid) or pid in seen:
            raise ValueError('Unsafe or duplicate program id')
        seen.add(pid)
        parsed=urlparse(program.get('url',''))
        if parsed.scheme!='https' or parsed.netloc!='catalog.unc.edu' or parsed.path.rstrip('/')!='/undergraduate/programs-study/'+pid:
            raise ValueError('Program source URL mismatch')
        path=source_dir/(pid+'.html')
        if not path.is_file():
            records.append({'id':pid,'status':'missing','reason':'Official page snapshot not supplied'})
            continue
        raw=path.read_bytes()
        if len(raw)>2_000_000:raise ValueError('Oversized source page')
        try:html=raw.decode('utf-8')
        except UnicodeDecodeError:raise ValueError('Source page must be UTF-8')
        status,reason=assess_page(program,html)
        digest=hashlib.sha256(raw).hexdigest()
        records.append({'id':pid,'status':status,'reason':reason,'sha256':digest,'source_url':program['url']})
        if status=='candidate':payloads[pid]=raw
    counts={k:sum(x['status']==k for x in records) for k in ('candidate','missing','invalid','edition_unconfirmed','title_mismatch','requirements_unconfirmed')}
    if strict and counts['candidate']!=len(programs):
        raise ValueError(f'Incomplete source batch: {counts["candidate"]}/{len(programs)} candidate pages. No output written.')
    # Avoid a stale prior batch being mistaken for current evidence.
    # This output folder must be dedicated to catalog evidence only.
    if output_dir.exists():
        old_pages={p.stem for p in output_dir.glob('*.html')}
        stale=old_pages-set(payloads)
        if stale:
            raise ValueError('Stale evidence in output directory: '+', '.join(sorted(stale))+'; use a clean output directory')
    # Stage in same parent and replace only the manifest after evidence is written.
    output_dir.mkdir(parents=True,exist_ok=True)
    for pid,raw in payloads.items():
        dest=output_dir/(pid+'.html')
        temp=output_dir/(pid+'.html.tmp')
        temp.write_bytes(raw);temp.replace(dest)
    report={'catalog_year':'2026-2027','total_programs':len(programs),'counts':counts,
            'reviewed_programs':0,'plan_ready_programs':0,'records':records,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'notice':'Source snapshots are NOT verified requirements and confer no scheduling approval.'}
    temp=output_dir/'batch_manifest.json.tmp';temp.write_text(json.dumps(report,indent=2),encoding='utf-8')
    temp.replace(output_dir/'batch_manifest.json')
    return report

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--registry',required=True);p.add_argument('--sources',required=True);p.add_argument('--output',required=True)
    p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
    result=batch_import(a.registry,a.sources,a.output,strict=not a.allow_partial)
    print(json.dumps({'total':result['total_programs'],'counts':result['counts'],'verified':0},indent=2))
if __name__=='__main__':main()
