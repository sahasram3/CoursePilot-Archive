"""Offline-first university-wide program registry. Discovery != verified planning."""
import argparse
import json
from pathlib import Path
from .program_coverage import registry_from_index, coverage


def ingest_html(html, *, minimum=1):
    result = registry_from_index(html)
    if result['total_discovered'] < minimum:
        raise ValueError(f'Only {result["total_discovered"]} program links found; expected at least {minimum}. Registry not replaced.')
    ids = [p['id'] for p in result['programs']]
    if len(ids) != len(set(ids)):
        raise ValueError('Conflicting program identifiers; registry not replaced')
    result['source_format'] = 'official_index_html'
    result['verification_notice'] = 'Discovered programs are NOT approved for academic scheduling.'
    return result


def write_registry_atomic(registry, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.tmp')
    temporary.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(target)


def read_registry(path):
    path = Path(path)
    if not path.exists():
        return {'catalog_year':'2026-2027','programs':[], 'total_discovered':0,
                'verification_notice':'No live index imported; supply official UNC index HTML.'}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data.get('programs'), list):
        raise ValueError('Invalid registry format')
    return data


def validate_selection(programs, registry):
    if not isinstance(programs, list) or not all(isinstance(p, dict) for p in programs):
        raise ValueError('Programs must be a list of program selections')
    if not 1 <= len(programs) <= 3:
        raise ValueError('Choose between one and three programs')
    kinds = [p.get('kind') for p in programs]
    majors, minors = kinds.count('major'), kinds.count('minor')
    if (majors, minors) not in {(1,0),(2,0),(1,1),(2,1),(1,2)}:
        raise ValueError('Allowed combinations: one or two majors and up to two minors, maximum three programs')
    ids = [p.get('id') for p in programs]
    if any(not isinstance(pid, str) or not pid or len(pid)>160 for pid in ids):
        raise ValueError('Each program ID must be a nonempty string')
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate program selection')
    lookup = {p['id']:p for p in registry['programs']}
    for item in programs:
        if item['id'] not in lookup:
            raise ValueError(f'Unknown program: {item["id"]}')
        if lookup[item['id']]['kind'] != item['kind']:
            raise ValueError('Program kind mismatch')
    return {'valid_combination':True, 'plan_ready':False,
            'notice':'Combination structure is valid; program-specific compatibility and degree restrictions have NOT been verified.'}


def main():
    parser = argparse.ArgumentParser(description='Import a saved official UNC program index HTML. No scraping required.')
    parser.add_argument('--html',required=True,help='Local saved HTML of https://catalog.unc.edu/undergraduate/programs-study/')
    parser.add_argument('--output',default='data/unc_program_registry.json')
    parser.add_argument('--minimum',type=int,default=100,help='Safety threshold to reject partial pages (default 100)')
    args=parser.parse_args()
    registry=ingest_html(Path(args.html).read_text(encoding='utf-8'),minimum=args.minimum)
    write_registry_atomic(registry,args.output)
    print(json.dumps({'discovered':registry['total_discovered'],'saved_to':args.output,'verified':0},indent=2))

if __name__=='__main__':main()
