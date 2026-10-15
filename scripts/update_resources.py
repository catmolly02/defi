"""Aggregate RSS/Atom/RDF metadata into a static dashboard and apply human edits."""
import concurrent.futures
import hashlib
import html
import json
import re
import shutil
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from tagging import suggest_tags,apply_override

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'dist/data'

def read(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def canonical_url(url):
    parts=urllib.parse.urlsplit(url)
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:raise ValueError('Invalid URL')
    pairs=[(k,v)for k,v in urllib.parse.parse_qsl(parts.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urllib.parse.urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path or '/',urllib.parse.urlencode(sorted(pairs)),''))

def resource_id(url):return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:24]

def text(value,limit=1000):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',value or '')).split())[:limit]

def date_value(value):
    value=(value or '').strip()
    if not value:return None
    for fmt in ('%Y%m%d%H%M%S','%Y-%m-%d %H:%M:%S','%Y%m%d','%Y-%m-%d'):
        try:
            from zoneinfo import ZoneInfo
            return datetime.strptime(value,fmt).replace(tzinfo=ZoneInfo('Asia/Seoul')).astimezone(timezone.utc).isoformat()
        except ValueError:pass
    try:d=parsedate_to_datetime(value)
    except (TypeError,ValueError):
        try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:return None
    return d.replace(tzinfo=d.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()

def child_value(item,names):
    for node in item:
        name=node.tag.split('}')[-1]
        if name in names:
            if name=='link' and node.attrib.get('rel','alternate') not in ('alternate',''):continue
            value=node.attrib.get('href') if name=='link' else None
            value=value or ''.join(node.itertext())
            if value.strip():return value
    return ''

def parse_feed(data,source,catalog):
    if b'<!ENTITY' in data.upper():raise ValueError('Entities not accepted')
    root=ET.fromstring(data);rows=[]
    for item in root.iter():
        if item.tag.split('}')[-1] not in ('item','entry'):continue
        title=text(child_value(item,('title',)),250)
        link=child_value(item,('link',))
        try:url=canonical_url(urllib.parse.urljoin(source['url'],link))
        except ValueError:continue
        if not title or not link:continue
        raw_date=child_value(item,('pubDate','published','date','updated'))
        summary=text(child_value(item,('description','summary')),500)
        row={'id':resource_id(url),'title':title,'url':url,'summary':summary,'source':source['name'],'source_ids':[source['id']],'region':source['region'],'category':source.get('category','industry'),'kind':source.get('kind','news'),'published_at':date_value(raw_date),'collected_at':datetime.now(timezone.utc).isoformat(),'hidden':False}
        # RSS descriptions are used for classification only, never published as copied article bodies.
        suggestion=suggest_tags(row,catalog,source.get('default_tags',[]))
        row.update(tags=suggestion['tags'],auto_tags=suggestion['tags'],tag_method=suggestion['method'],summary='')
        if '/event-info/' in url:row.update(kind='event',category='support')
        elif '/videoarticle/' in url:row['kind']='link'
        if re.search(r'입법예고|규정변경예고|법률안|시행령|시행규칙',title):row['category']='legislation'
        rows.append(row)
    if not rows:raise ValueError('No entries')
    return rows[:45]

def fetch_source(source,catalog):
    request=urllib.request.Request(source['url'],headers={'User-Agent':'DEFI-Research-Dashboard/1.0 (RSS metadata reader)'})
    with urllib.request.urlopen(request,timeout=20)as response:data=response.read(3_000_000)
    return parse_feed(data,source,catalog)

def combine(rows,catalog,editorial):
    merged={}
    for row in rows:
        key=resource_id(row['url']);row=dict(row,id=key)
        if key in merged:
            old=merged[key];old['tags']=sorted(set(old['tags'])|set(row['tags']));old['auto_tags']=list(old['tags']);old['source_ids']=sorted(set(old.get('source_ids',[])+row.get('source_ids',[])))
        else:merged[key]=row
    for manual in editorial.get('manual_resources',[]):
        try:
            url=canonical_url(manual.get('url',''));key=resource_id(url)
            title=text(manual.get('title',''),250)
            if not title:continue
            base=dict(id=key,title=title,url=url,summary=text(manual.get('summary',''),1000),source=text(manual.get('source','직접 등록'),80),source_ids=[],region=manual.get('region','domestic'),category=manual.get('category','industry'),kind=manual.get('kind','link'),published_at=date_value(manual.get('published_at','')),collected_at=manual.get('collected_at') or datetime.now(timezone.utc).isoformat(),hidden=False)
            suggestion=suggest_tags(base,catalog);base.update(tags=suggestion['tags'],auto_tags=suggestion['tags'],tag_method=suggestion['method'])
            # User-supplied categories/tags are still validated.
            merged[key]=apply_override(base,manual,catalog)
        except (ValueError,TypeError):continue
    result=[apply_override(row,editorial.get('overrides',{}).get(key),catalog)for key,row in merged.items()]
    result.sort(key=lambda r:r.get('published_at')or r['collected_at'],reverse=True)
    return result[:1000]

def main():
    catalog=read(ROOT/'config/catalog.json',{});sources=read(ROOT/'config/sources.json',[])
    editorial=read(ROOT/'config/editorial.json',{'overrides':{},'manual_resources':[]})
    cache=read(DATA/'rss-cache.json',{});health=[]
    enabled=[s for s in sources if s.get('enabled',True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:
        futures={pool.submit(fetch_source,s,catalog):s for s in enabled}
        for future in concurrent.futures.as_completed(futures):
            source=futures[future];key=source['id'];stamp=datetime.now(timezone.utc).isoformat()
            try:
                rows=future.result();cache[key]={'rows':rows,'last_success':stamp}
                health.append({'id':key,'name':source['name'],'status':'ok','count':len(rows),'last_success':stamp})
                print(source['name'],len(rows))
            except Exception as error:
                old=cache.get(key,{})
                health.append({'id':key,'name':source['name'],'status':'cached' if old.get('rows') else 'error','count':len(old.get('rows',[])),'last_success':old.get('last_success')})
                print(f'::warning::{key} unavailable ({type(error).__name__}); keeping cache')
    rows=[row for s in enabled for row in cache.get(s['id'],{}).get('rows',[])]
    result=combine(rows,catalog,editorial)
    write(DATA/'rss-cache.json',cache)
    write(DATA/'resources.json',{'schema_version':1,'updated_at':datetime.now(timezone.utc).isoformat(),'resources':result,'sources':sorted(health,key=lambda s:s['name'])})
    write(DATA/'catalog.json',catalog);write(DATA/'editorial.json',editorial)
    print('Dashboard resources:',len(result))

if __name__=='__main__':main()
