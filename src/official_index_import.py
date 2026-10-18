"""Safe import of a saved official UNC index or a fetched official HTML response.

No reviewer approval is inferred. Download only from the canonical UNC URL.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from .catalog_registry import ingest_html, write_registry_atomic

INDEX='https://catalog.unc.edu/undergraduate/programs-study/'

def import_index(html, *, minimum=100):
    if not isinstance(html,str) or len(html)<100:
        raise ValueError('Missing or truncated catalog HTML')
    registry=ingest_html(html,minimum=minimum)
    registry['source_url']=INDEX
    registry['source_sha256']=hashlib.sha256(html.encode('utf-8')).hexdigest()
    registry['imported_at_utc']=datetime.now(timezone.utc).isoformat()
    registry['approval_status']='discovery_only'
    for p in registry['programs']:
        p['plan_ready']=False
        p['requirements_status']='unreviewed'
    return registry

def download_official_index(*, timeout=20):
    req=Request(INDEX,headers={'User-Agent':'PreReqPathResearch/0.24 (academic catalog metadata; respectful one-page request)'})
    with urlopen(req,timeout=timeout) as response:
        final=response.geturl()
        if final.rstrip('/')!=INDEX.rstrip('/'):
            raise ValueError('Unexpected redirect from official index')
        body=response.read(3_000_001)
        if len(body)>3_000_000:
            raise ValueError('Unexpectedly large catalog response')
        content_type=response.headers.get('Content-Type','')
        if 'html' not in content_type.lower():
            raise ValueError('Official index response is not HTML')
        return body.decode('utf-8')

def main():
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--fetch',action='store_true')
    group.add_argument('--html',type=Path)
    ap.add_argument('--output',type=Path,default=Path('data/unc_program_registry.json'))
    ap.add_argument('--minimum',type=int,default=100)
    args=ap.parse_args()
    html=download_official_index() if args.fetch else args.html.read_text(encoding='utf-8')
    registry=import_index(html,minimum=args.minimum)
    write_registry_atomic(registry,args.output)
    print(json.dumps({'discovered':registry['total_discovered'], 'verified':0,
                      'sha256':registry['source_sha256'],'output':str(args.output)},indent=2))
if __name__=='__main__':main()
