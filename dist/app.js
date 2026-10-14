const coins = [['bitcoin','비트코인','BTC','₿'], ['ethereum','이더리움','ETH','Ξ'], ['ripple','리플','XRP','X'], ['solana','솔라나','SOL','◎']];
const periods = [[1,'하루'],[7,'일주일'],[30,'한 달'],[365,'1년']];
let currency = 'usd', selected = 'bitcoin', period = 7, market = [], reports = [];
let chartRequest = 0, marketRequest = 0, newsRequest = 0, news = [], newsFilter = '전체', newsExpanded = false;
const chartCache = new Map();
const $ = id => document.getElementById(id);
const money = n => Number.isFinite(n) ? new Intl.NumberFormat('ko-KR', {style:'currency',currency:currency.toUpperCase(),maximumFractionDigits:currency==='krw'?0:2}).format(n) : '—';
const compact = n => Number.isFinite(n) ? new Intl.NumberFormat('ko-KR', {notation:'compact', maximumFractionDigits:1}).format(n) : '—';
const dateText = value => {const d=new Date(value);return value && !Number.isNaN(d.valueOf()) ? d.toLocaleString('ko-KR') : '시각 미확인'};
async function readData(path) {
  const response = await fetch(path, {cache:'no-store'});
  if (!response.ok) throw new Error('HTTP '+response.status);
  return response.json();
}
function selectCoin(id) { selected=id; render(); loadChart(); }
function render() {
  $('cards').replaceChildren(); $('coin-tabs').replaceChildren();
  for (const [id,name,ticker,symbol] of coins) {
    const c = market.find(x=>x.id===id)||{}, change=c.price_change_percentage_24h;
    const button=document.createElement('button'); button.className='coin'+(id===selected?' active':'');
    button.setAttribute('aria-pressed',String(id===selected));
    button.innerHTML='<div class="coin-name"><span class="coin-symbol">'+symbol+'</span>'+name+'<span class="ticker">'+ticker+'</span></div><div class="price">'+money(c.current_price)+'</div><div class="change '+(Number.isFinite(change)?(change>=0?'up':'down'):'')+'">'+(Number.isFinite(change)?(change>=0?'▲ ':'▼ ')+Math.abs(change).toFixed(2)+'%':'—')+' <span class="change">24시간</span></div><div class="metrics"><span>시가총액<b>'+compact(c.market_cap)+'</b></span><span>24h 거래량<b>'+compact(c.total_volume)+'</b></span></div>';
    button.onclick=()=>selectCoin(id); $('cards').append(button);
    const tab=document.createElement('button'); tab.textContent=ticker; tab.className=id===selected?'active':'';
    tab.setAttribute('aria-pressed',String(id===selected)); tab.onclick=button.onclick; $('coin-tabs').append(tab);
  }
}
function renderPeriods() {
  $('period-tabs').replaceChildren();
  for(const [days,label] of periods) {
    const button=document.createElement('button'); button.textContent=label;button.className=days===period?'active':'';
    button.setAttribute('aria-pressed',String(days===period));
    button.onclick=()=>{period=days;renderPeriods();loadChart()};$('period-tabs').append(button);
  }
}
function chartMessage(message) {
  $('chart').className='chart-empty';$('chart').textContent=message;$('range').textContent='';$('chart-updated').textContent='';
}
function draw(prices, fetchedAt) {
  const values=prices.map(p=>p[1]), lo=Math.min(...values), hi=Math.max(...values), span=hi-lo||1;
  const first=prices[0][0], last=prices[prices.length-1][0], duration=last-first||1;
  const points=prices.map(([stamp,value])=>[10+(stamp-first)/duration*940,220-(value-lo)/span*185]);
  const path=points.map((point,index)=>(index?'L':'M')+point.join(',')).join(' ');
  const name=coins.find(c=>c[0]===selected)[1];
  const axis=stamp=>new Date(stamp).toLocaleString('ko-KR',period===1?{hour:'2-digit',minute:'2-digit'}:{month:'numeric',day:'numeric'});
  $('chart').className='';
  $('chart').innerHTML='<svg viewBox="0 0 960 270" role="img" aria-label="'+name+' '+period+'일 가격 그래프"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#239b8b" stop-opacity=".18"/><stop offset="1" stop-color="#239b8b" stop-opacity="0"/></linearGradient></defs>'+[35,95,155,220].map(y=>'<path d="M10 '+y+' H950" stroke="#edf1f4"/>').join('')+'<path d="'+path+' L950,235 L10,235 Z" fill="url(#chart-fill)"/><path d="'+path+'" fill="none" stroke="#239b8b" stroke-width="2.5"/>'+[0,.5,1].map(f=>'<text x="'+(10+940*f)+'" y="262" text-anchor="'+(f===0?'start':f===1?'end':'middle')+'" fill="#71818b" font-size="12">'+axis(first+duration*f)+'</text>').join('')+'</svg>';
  const change=values[0]>0?(values[values.length-1]/values[0]-1)*100:null;
  $('range').textContent='최저 '+money(lo)+' · 최고 '+money(hi)+(change===null?'':' · 기간 변동 '+(change>=0?'+':'')+change.toFixed(2)+'%');
  $('chart-updated').textContent='차트 수집 '+dateText(fetchedAt);
}
async function loadChart() {
  const version=++chartRequest, requestCurrency=currency, requestPeriod=period, requestCoin=selected;
  $('chart-title').textContent=coins.find(c=>c[0]===selected)[1]+' 가격 추이';
  $('chart-subtitle').textContent='최근 '+period+'일 · '+currency.toUpperCase();
  chartMessage('가격 그래프를 불러오는 중입니다.');
  try {
    const path='data/charts-'+requestCurrency+'-'+requestPeriod+'.json';
    if(!chartCache.has(path)) chartCache.set(path,readData(path).catch(error=>{chartCache.delete(path);throw error}));
    const data=await chartCache.get(path);
    if(version!==chartRequest)return;
    const coin=data.coins?.[requestCoin];
    const prices=(coin?.prices||[]).filter(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&p[0]>0&&p[1]>=0).sort((a,b)=>a[0]-b[0]);
    if(prices.length<2)throw new Error('차트 없음');
    draw(prices,coin.fetched_at);
  } catch {
    if(version===chartRequest)chartMessage('이 기간의 가격 자료가 아직 없습니다. 다음 데이터 갱신 후 다시 확인해 주세요.');
  }
}
async function loadMarkets() {
  const version=++marketRequest, requestCurrency=currency;
  market=[];render();$('status').textContent='CoinGecko 시장 데이터를 확인하고 있습니다.';
  try {
    const data=await readData('data/markets-'+requestCurrency+'.json');
    if(version!==marketRequest)return;
    if(!Array.isArray(data.coins)||!coins.every(c=>data.coins.some(x=>x.id===c[0])))throw new Error();
    market=data.coins;$('status').textContent='● CoinGecko · 자료 수집 '+dateText(data.fetched_at)+' · 거래소 실시간 시세와 다를 수 있습니다.';
  } catch {
    if(version===marketRequest)$('status').textContent='시장 데이터를 불러오지 못했습니다. 최근 자동 배포의 CoinGecko 수집 결과를 확인해 주세요.';
  } finally {if(version===marketRequest)render()}
}
function renderNewsFilters() {
  $('news-filters').replaceChildren();
  for(const label of ['전체','BTC','ETH','XRP','SOL']) {
    const button=document.createElement('button');button.textContent=label;button.className=label===newsFilter?'active':'';
    button.setAttribute('aria-pressed',String(label===newsFilter));
    button.onclick=()=>{newsFilter=label;newsExpanded=false;renderNewsFilters();renderNews()};$('news-filters').append(button);
  }
}
function renderNews() {
  const list=$('news-list');list.replaceChildren();
  const filtered=news.filter(a=>newsFilter==='전체'||a.tags?.includes(newsFilter));
  for(const item of newsExpanded?filtered:filtered.slice(0,6)) {
    const article=document.createElement('article');article.className='news-card';
    const meta=document.createElement('div');meta.className='news-meta';meta.textContent='CoinDesk · '+dateText(item.published_at);
    const heading=document.createElement('h3'),link=document.createElement('a');link.textContent=item.title;link.href=item.url;link.target='_blank';link.rel='noopener';heading.append(link);
    const tags=document.createElement('p');tags.className='news-tags';tags.textContent=item.tags?.join(' · ')||'디지털자산';
    const more=document.createElement('a');more.href=item.url;more.target='_blank';more.rel='noopener';more.textContent='원문 읽기 ↗';more.className='news-source';
    article.append(meta,heading,tags,more);list.append(article);
  }
  if(!filtered.length) {const empty=document.createElement('p');empty.className='empty';empty.textContent=news.length?'해당 코인의 최신 기사가 없습니다.':'아직 수집된 기사가 없습니다.';list.append(empty)}
  $('more-news').hidden=filtered.length<=6;$('more-news').textContent=newsExpanded?'접기 ↑':'뉴스 더보기 ↓';$('more-news').setAttribute('aria-expanded',String(newsExpanded));
}
async function loadNews() {
  const version=++newsRequest;$('news-status').textContent='CoinDesk RSS를 확인하고 있습니다.';
  try {
    const data=await readData('data/news.json');if(version!==newsRequest)return;
    if(!Array.isArray(data.articles))throw new Error();
    news=data.articles.filter(a=>{try{const u=new URL(a.url);return typeof a.title==='string'&&u.protocol==='https:'&&['www.coindesk.com','coindesk.com'].includes(u.hostname)}catch{return false}});
    $('news-status').textContent=data.fetched_at?'RSS 수집 '+dateText(data.fetched_at)+' · 최신 기사 목록이며 중요도 순위는 아닙니다.':'RSS 수집 대기';
  } catch {if(version===newsRequest){news=[];$('news-status').textContent='뉴스 목록을 불러오지 못했습니다. 다음 자동 갱신 후 다시 확인해 주세요.'}}
  if(version===newsRequest)renderNews();
}
function reportCard(r,latest=false){const a=document.createElement('article');a.className='report';const cover=document.createElement('div');cover.className='pdf-cover';cover.textContent='PDF';if(r.cover){const img=document.createElement('img');img.src=encodeURI(r.cover);img.alt=r.title+' 표지';img.loading='lazy';img.onerror=()=>{cover.className='pdf-cover';cover.textContent='PDF'};cover.replaceChildren(img);cover.className='';}a.append(cover);const content=document.createElement('div');const tag=document.createElement('span');tag.className='tag';tag.textContent=(latest?'최신 자료 · ':'')+(r.date_label||'등록일')+' '+r.period;const title=document.createElement('h3');title.textContent=r.title;const desc=document.createElement('p');desc.textContent=r.description+' · '+(r.size/1024/1024).toFixed(1)+' MB';const actions=document.createElement('div');actions.className='report-actions';for(const [text,download]of [['PDF 읽기 ↗',false],['다운로드 ↓',true]]){const link=document.createElement('a');link.href=encodeURI(r.file).replace(/#/g,'%23').replace(/\?/g,'%3F');link.textContent=text;if(download)link.download=r.file.split('/').pop();else{link.target='_blank';link.rel='noopener'}actions.append(link)}content.append(tag,title,desc,actions);a.append(content);return a}function renderArchive(){const list=$('archive-list');list.replaceChildren();const q=$('search').value.toLowerCase();const filtered=reports.filter(r=>(r.title+' '+r.period).toLowerCase().includes(q));for(const r of filtered)list.append(reportCard(r));if(!filtered.length){const p=document.createElement('p');p.className='empty';p.textContent='검색 결과가 없습니다.';list.append(p)}}function renderReports(){$('report-list').replaceChildren();if(reports.length)$('report-list').append(reportCard(reports[0],true));else $('report-list').textContent='등록된 PDF가 없습니다.';$('report-count').textContent=reports.length+'개';$('more-reports').disabled=!reports.length;renderArchive()}$('more-reports').onclick=()=>{const open=$('report-archive').hidden;$('report-archive').hidden=!open;$('more-reports').textContent=open?'접기 ↑':'더보기 →';$('more-reports').setAttribute('aria-expanded',String(open));};

$('currency').onchange=e=>{currency=e.target.value;loadMarkets();loadChart()};
$('refresh').onclick=async()=>{ $('refresh').disabled=true;chartCache.clear();await Promise.allSettled([loadMarkets(),loadChart(),loadNews()]);$('refresh').disabled=false; };
$('search').oninput=renderArchive;
$('more-news').onclick=()=>{newsExpanded=!newsExpanded;renderNews()};
readData('reports.json').then(data=>{reports=data;renderReports()}).catch(()=>{$('report-list').textContent='간행물 목록을 불러오지 못했습니다. 새로고침해 주세요.'});
render();renderPeriods();renderNewsFilters();loadMarkets();loadChart();loadNews();
