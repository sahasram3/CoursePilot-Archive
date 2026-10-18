"""Conservative candidate extraction from UNC catalog evidence.

Candidates are quotations for review, NEVER validated academic rules.
"""
import argparse
import json
import re
from pathlib import Path
from .catalog_registry import write_registry_atomic

COURSE = re.compile(r'\b([A-Z]{2,5})\s*([0-9]{3}[A-Z]?)\b')
EXACT = re.compile(r'^\s*([A-Z]{2,5})\s*([0-9]{3}[A-Z]?)\s*$')
CREDIT = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*$')
RANGE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*$')
CHOICE = re.compile(r'\b(?:or|one of|choose|select|either|any|at least|additional|electives?|above|higher|minimum|from the following)\b', re.I)
GRADE = re.compile(r'\b(?:minimum grade|grade of|[A-D][+-]? or better|[A-D][+-]? minimum)\b', re.I)
RESTRICT = re.compile(r'\b(?:residen\w*|double.count\w*|may not|cannot|restricted|permission|approval|concentration|track|waiver|substitut\w*)\b',re.I)
PREREQ = re.compile(r'\b(?:pre.?requisit\w*|co.?requisit\w*|prior to|must complete|placement)\b',re.I)


def classify_row(cells):
    """Classify evidence row; ambiguous rows stay ambiguous, never forced to required."""
    if not cells: return None
    raw=' | '.join(cells)
    codes=list(dict.fromkeys(f'{a} {b}' for a,b in COURSE.findall(raw.upper())))
    if not codes: return None
    left=cells[0].strip()
    exact=EXACT.fullmatch(left.upper())
    credit_cell=cells[-1].strip() if len(cells)>1 else ''
    credit=CREDIT.fullmatch(credit_cell)
    variable=RANGE.fullmatch(credit_cell)
    flags=[]
    if CHOICE.search(raw): flags.append('choice_or_elective_language')
    if GRADE.search(raw): flags.append('grade_language')
    if RESTRICT.search(raw): flags.append('restriction_language')
    if PREREQ.search(raw): flags.append('prerequisite_language')
    if len(codes)>1: flags.append('multiple_course_codes')
    if variable: flags.append('variable_credit_range')
    if not credit and not variable: flags.append('credits_not_single_numeric_value')
    if exact and len(codes)==1 and credit and not flags:
        kind='single_course_candidate'
    elif CHOICE.search(raw) or len(codes)>1:
        kind='choice_or_group_candidate'
    else:
        kind='ambiguous_course_candidate'
    return {'candidate_type':kind,'course_codes':codes,
            'credit_hours_observed':float(credit.group(1)) if credit else None,
            'credit_range_observed':[float(x) for x in variable.groups()] if variable else None,
            'verbatim_cells':cells,'review_flags':flags}


def extract_candidates(evidence):
    """Take v1.3 review evidence and emit review-only candidates with provenance."""
    result={'id':evidence['id'],'name':evidence['name'],'url':evidence['url'],
            'catalog_year_requested':evidence.get('catalog_year_requested','2026-2027'),
            'source_sha256':evidence.get('source_sha256'),
            'source_status':evidence.get('review_status','unknown'),
            'candidates':[], 'warnings':[], 'plan_ready':False,
            'approved_rules':0, 'review_status':'needs_human_review'}
    if evidence.get('review_status')=='source_missing' or not evidence.get('source_sha256'):
        result['review_status']='source_missing'
        result['warnings'].append('source_missing')
        return result
    if not evidence.get('catalog_year_visible'):
        result['warnings'].append('catalog_year_not_confirmed')
    for table_index,table in enumerate(evidence.get('tables',[])):
        for row_index,cells in enumerate(table):
            candidate=classify_row(cells)
            if candidate:
                candidate.update({'evidence_type':'table_row','table_index':table_index,'row_index':row_index,
                                  'source_sha256':evidence['source_sha256']})
                result['candidates'].append(candidate)
    excerpt=evidence.get('evidence_excerpt','')
    # A text excerpt is flattened source text; flag relevant passages, not rules.
    sentences=re.split(r'(?<=[.!?])\s+',excerpt)
    for sentence_index,sentence in enumerate(sentences):
        if not (GRADE.search(sentence) or RESTRICT.search(sentence) or PREREQ.search(sentence)):
            continue
        if len(sentence)>1000:
            result['warnings'].append('long_text_passage_requires_manual_review')
            continue
        tags=[]
        if GRADE.search(sentence):tags.append('grade')
        if RESTRICT.search(sentence):tags.append('restriction')
        if PREREQ.search(sentence):tags.append('prerequisite_or_corequisite')
        result['candidates'].append({'candidate_type':'policy_text_candidate','evidence_type':'text_excerpt',
           'sentence_index':sentence_index,'verbatim_text':sentence,'tags':tags,
           'course_codes':list(dict.fromkeys(f'{a} {b}' for a,b in COURSE.findall(sentence.upper()))),
           'source_sha256':evidence['source_sha256'],'review_flags':['unstructured_prose_requires_review']})
    if not result['candidates']:result['warnings'].append('no_rule_candidates_detected')
    return result


def build_candidate_queue(review_queue):
    items=[extract_candidates(item) for item in review_queue.get('programs',[])]
    return {'catalog_year_requested':review_queue.get('catalog_year_requested','2026-2027'),
       'programs_discovered':len(items),'programs_with_candidates':sum(bool(p['candidates']) for p in items),
       'candidate_count':sum(len(p['candidates']) for p in items),
       'approved_for_planning':0,'notice':'Machine-extracted review candidates only. No rules approved; no graduation plans certified.',
       'programs':items}


def main():
    ap=argparse.ArgumentParser(description='Convert v1.3 evidence into unapproved review candidates')
    ap.add_argument('--review-queue',required=True)
    ap.add_argument('--output',default='data/rule_candidate_queue.json')
    args=ap.parse_args()
    data=json.loads(Path(args.review_queue).read_text(encoding='utf-8'))
    output=build_candidate_queue(data)
    write_registry_atomic(output,args.output)
    print(json.dumps({k:output[k] for k in ('programs_discovered','programs_with_candidates','candidate_count','approved_for_planning')},indent=2))

if __name__=='__main__':main()
