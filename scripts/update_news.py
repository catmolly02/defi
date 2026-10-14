"""Collect CoinDesk's official RSS titles and source links, without AI or an API key."""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = 'https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml'
OUTPUT = Path(__file__).resolve().parents[1] / 'dist' / 'data' / 'news.json'


def parse_feed(xml):
    root = ET.fromstring(xml)
    news = {}
    for item in root.findall('./channel/item'):
        title = ' '.join((item.findtext('title') or '').split())
        link = (item.findtext('link') or '').strip()
        parsed = urllib.parse.urlsplit(link)
        if not title or parsed.scheme != 'https' or parsed.hostname not in ('coindesk.com', 'www.coindesk.com'):
            continue
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '')
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            published = date.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, IndexError):
            continue
        canonical = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
        search = title.lower()
        tags = [tag for tag, pattern in [('BTC', r'\b(bitcoin|btc)\b'),
                 ('ETH', r'\b(ethereum|ether|eth)\b'), ('XRP', r'\b(ripple|xrp)\b'),
                 ('SOL', r'\b(solana|sol)\b')] if re.search(pattern, search)]
        article = {'title': title, 'url': canonical, 'published_at': published,
                   'source': 'CoinDesk', 'tags': tags}
        if canonical not in news or published > news[canonical]['published_at']:
            news[canonical] = article
    return sorted(news.values(), key=lambda x: x['published_at'], reverse=True)[:30]


def main():
    try:
        request = urllib.request.Request(FEED_URL, headers={'User-Agent': 'DEFI-News/1.0 (+RSS reader)'})
        with urllib.request.urlopen(request, timeout=30) as response:
            items = parse_feed(response.read(2_000_000))
        if not items:
            raise ValueError('No valid articles')
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT.with_suffix('.tmp')
        temporary.write_text(json.dumps({'source': 'CoinDesk', 'feed_url': FEED_URL,
                            'fetched_at': datetime.now(timezone.utc).isoformat(), 'articles': items},
                            ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(OUTPUT)
        print(f'Collected {len(items)} CoinDesk RSS articles')
    except Exception as error:
        print(f'::warning::CoinDesk RSS unavailable ({type(error).__name__}); keeping any cached news')
        if not OUTPUT.exists():
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(json.dumps({'source': 'CoinDesk', 'articles': [], 'fetched_at': None}), encoding='utf-8')


if __name__ == '__main__':
    main()
