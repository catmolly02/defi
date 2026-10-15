"""Rule-based tag suggestions. Replace suggest_tags with a server-side AI adapter later.
Human overrides are applied separately and always win, including an empty tag list.
Never call an AI API or embed an AI key in browser code.
"""
import re

def match_keyword(text, keyword):
    keyword=keyword.lower()
    if re.fullmatch(r'[a-z0-9-]+',keyword):
        return re.search(r'(?<![a-z0-9])'+re.escape(keyword)+r'(?![a-z0-9])',text) is not None
    return keyword in text

def suggest_tags(resource, catalog, defaults=()):
    text=(resource.get('title','')+' '+resource.get('summary','')).lower()
    known={c['id'] for c in catalog['councils']}
    # Feed names are context only: a broad RSS channel is not evidence of topic relevance.
    result=set()
    for council in catalog['councils']:
        if any(match_keyword(text,k) for k in council.get('keywords',[])):
            result.add(council['id'])
    return {'tags':sorted(result),'method':'rules-v2'}

def apply_override(resource, override, catalog):
    if not isinstance(override,dict):return resource
    result=dict(resource);known={c['id'] for c in catalog['councils']}
    if isinstance(override.get('tags'),list):
        result['tags']=[tag for tag in override['tags'] if tag in known]
        result['tag_method']='manual'
    for field,choices in [('region',('domestic','overseas')),('category',[c['id'] for c in catalog['categories']]),('kind',('news','report','announcement','event','data','link'))]:
        if override.get(field) in choices:result[field]=override[field]
    for field,limit in [('title',250),('summary',1000)]:
        if isinstance(override.get(field),str):result[field]=override[field].strip()[:limit]
    if isinstance(override.get('hidden'),bool):result['hidden']=override['hidden']
    return result
