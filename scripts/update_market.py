import os,json,time,urllib.request
from pathlib import Path
key=os.environ.get('COINGECKO_API_KEY','')
if not key:
    print('API key not configured; publishing reports only')
    raise SystemExit(0)
pro=os.environ.get('COINGECKO_PLAN','demo')=='pro'
base='https://pro-api.coingecko.com' if pro else 'https://api.coingecko.com'
for currency in ('usd','krw'):
    url=base+'/api/v3/coins/markets?vs_currency='+currency+'&ids=bitcoin,ethereum,ripple,solana&sparkline=true'
    req=urllib.request.Request(url,headers={'x-cg-pro-api-key' if pro else 'x-cg-demo-api-key':key,'User-Agent':'DEFI-Market/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r: data=json.load(r)
    if not isinstance(data,list) or len(data)!=4: raise SystemExit('Incomplete CoinGecko response')
    Path('dist/data/markets-'+currency+'.json').write_text(json.dumps({'fetched_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'coins':data}),encoding='utf-8')
