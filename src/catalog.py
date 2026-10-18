"""UNC catalog discovery and conservative extraction. Requires requests and bs4."""
import json,re,datetime,urllib.parse
import requests
from bs4 import BeautifulSoup
BASE='https://catalog.unc.edu'
INDEX=BASE+'/undergraduate/programs-study/'
HEADERS={'User-Agent':'PreReqPathResearch/0.3 (educational prototype; respect robots.txt)'}

def discover(html):
    soup=BeautifulSoup(html,'html.parser'); found={}
    for a in soup.select('a[href]'):
        url=urllib.parse.urljoin(BASE,a['href']).split('#')[0].split('?')[0]
        path=urllib.parse.urlparse(url).path
        if not url.startswith(BASE+'/undergraduate/programs-study/') or path.rstrip('/')=='/undergraduate/programs-study': continue
        if not re.search(r'(major|minor)',path,re.I) or path.endswith('.pdf'): continue
        name=a.get_text(' ',strip=True)
        if not name: continue
        found[url]={'name':name,'url':url,'kind':'minor' if 'minor' in path else 'major','status':'unreviewed'}
    return sorted(found.values(),key=lambda x:x['name'])

def extract_page(html,url):
    soup=BeautifulSoup(html,'html.parser')
    for x in soup(['script','style','nav','footer']):x.decompose()
    title=(soup.find('h1') or soup.find('title'))
    # Text is retained as evidence, NOT converted into purportedly verified rules.
    sections=[]
    for h in soup.find_all(['h2','h3']):
        if any(k in h.get_text(' ',strip=True).lower() for k in ('requirement','course','credit','major','minor')):
            text=[]
            for el in h.next_elements:
                if getattr(el,'name',None) in ('h2','h3'):break
                if getattr(el,'name',None) in ('p','li','tr'):
                    t=el.get_text(' ',strip=True)
                    if t and t not in text:text.append(t)
                if len(text)>=100:break
            sections.append({'heading':h.get_text(' ',strip=True),'text':'\n'.join(text)[:30000]})
    return {'url':url,'title':title.get_text(' ',strip=True) if title else '', 'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verification':'needs_human_review','sections':sections}

def crawl(limit=0):
    session=requests.Session();session.headers.update(HEADERS)
    # Respect robots.txt and site usage policies before running this crawler.
    r=session.get(INDEX,timeout=25);r.raise_for_status()
    programs=discover(r.text)
    if limit: programs=programs[:limit]
    pages=[]
    for p in programs:
        try:
            resp=session.get(p['url'],timeout=25);resp.raise_for_status()
            pages.append(extract_page(resp.text,p['url']))
        except requests.RequestException as exc:
            pages.append({'url':p['url'],'verification':'fetch_failed','error':str(exc)})
    return {'index':INDEX,'programs':programs,'pages':pages,'note':'Extracted text is unverified; no course requirements are automatically certified.'}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=5);ap.add_argument('--out',default='data/catalog_raw.json');args=ap.parse_args()
    result=crawl(args.limit)
    with open(args.out,'w') as f:json.dump(result,f,indent=2)
    print('Discovered:',len(result['programs']),'Fetched:',len(result['pages']))
