"""Conservative UNC catalog discovery + review queue. Never auto-certifies rules.
Run: python -m src.catalog_pipeline --limit 10 --output data/catalog_snapshot.json
"""
import argparse, datetime, hashlib, json, re, time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

BASE='https://catalog.unc.edu'
INDEX=BASE+'/undergraduate/programs-study/'
UA='PreReqPathAcademicResearch/0.5 (student prototype; contact repository maintainer)'

def parse_index(html):
    soup=BeautifulSoup(html,'html.parser'); records={}
    for a in soup.select('a[href]'):
        url=urljoin(BASE,a['href']).split('#')[0].split('?')[0]
        path=urlparse(url).path
        if not re.fullmatch(r'/undergraduate/programs-study/[^/]+/',path):continue
        slug=path.strip('/').split('/')[-1]
        if not re.search(r'(^|-)major(s)?(-|$)|(^|-)minor(-|$)',slug):continue
        name=a.get_text(' ',strip=True)
        if not name:continue
        kind='minor' if 'minor' in slug else 'major'
        records[url]={'name':name,'kind':kind,'url':url,'slug':slug,'review_status':'not_reviewed'}
    return sorted(records.values(),key=lambda r:r['url'])

def parse_page(html,url):
    soup=BeautifulSoup(html,'html.parser')
    for node in soup(['script','style','nav','footer']):node.decompose()
    title=soup.find('h1') or soup.find('title')
    tables=[]
    for table in soup.select('table'):
        rows=[]
        for tr in table.select('tr'):
            cells=[c.get_text(' ',strip=True) for c in tr.find_all(['th','td'],recursive=False)]
            if cells:rows.append(cells)
        if rows:tables.append(rows)
    evidence=soup.get_text(' ',strip=True)
    return {'url':url,'title':title.get_text(' ',strip=True) if title else '',
            'sha256':hashlib.sha256(html.encode()).hexdigest(),
            'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'review_status':'needs_human_review','tables':tables,
            'requirement_text_excerpt':evidence[:12000],
            'note':'Raw source evidence only. No prerequisite, credit or degree requirement is certified.'}

def crawl(limit=10,delay=1.5):
    session=requests.Session();session.headers['User-Agent']=UA
    robots=RobotFileParser();robots.set_url(BASE+'/robots.txt')
    try:robots.read()
    except Exception as exc:raise RuntimeError('Cannot verify robots policy; refusing crawl') from exc
    if not robots.can_fetch(UA,INDEX):raise PermissionError('Index disallowed by robots.txt')
    response=session.get(INDEX,timeout=20);response.raise_for_status()
    programs=parse_index(response.text)
    selected=programs if limit==0 else programs[:limit]
    pages=[]
    for item in selected:
        if not robots.can_fetch(UA,item['url']):
            pages.append({'url':item['url'],'review_status':'blocked_by_robots'});continue
        time.sleep(delay)
        try:
            r=session.get(item['url'],timeout=20);r.raise_for_status()
            pages.append(parse_page(r.text,item['url']))
        except requests.RequestException as exc:
            pages.append({'url':item['url'],'review_status':'fetch_failed','error':str(exc)})
    return {'catalog_year_requested':'2026-2027','year_verified':False,
            'source_index':INDEX,'discovered_programs':programs,'fetched_pages':pages,
            'warning':'The current site may show a different catalog edition. Verify edition and each rule before scheduling.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=10);ap.add_argument('--delay',type=float,default=1.5);ap.add_argument('--output',default='data/catalog_snapshot.json');a=ap.parse_args()
    from pathlib import Path
    result=crawl(a.limit,a.delay);Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Discovered',len(result['discovered_programs']),'programs; fetched',len(result['fetched_pages']),'pages; all unreviewed')
