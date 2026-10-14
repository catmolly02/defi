"""Collect public market snapshots and timestamped price charts; keys stay in Actions."""
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COINS = ('bitcoin', 'ethereum', 'ripple', 'solana')
CURRENCIES = ('usd', 'krw')
DATA_DIR = Path(__file__).resolve().parents[1] / 'dist' / 'data'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def valid_prices(raw):
    rows = {}
    for point in raw if isinstance(raw, list) else []:
        if (isinstance(point, list) and len(point) == 2
                and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                        and math.isfinite(x) for x in point)
                and point[0] > 0 and point[1] >= 0):
            rows[point[0]] = point[1]
    return [[stamp, rows[stamp]] for stamp in sorted(rows)]


def slice_prices(prices, days):
    if not prices:
        return []
    cutoff = prices[-1][0] - days * 86400000
    return [row for row in prices if row[0] >= cutoff]


class CoinGecko:
    def __init__(self, key, pro=False):
        self.base = 'https://pro-api.coingecko.com' if pro else 'https://api.coingecko.com'
        self.headers = {'x-cg-pro-api-key' if pro else 'x-cg-demo-api-key': key,
                        'User-Agent': 'DEFI-Market/2.0'}
        self.last_request = 0.0

    def get(self, path, **params):
        url = self.base + '/api/v3/' + path + '?' + urllib.parse.urlencode(params)
        for attempt in range(3):
            time.sleep(max(0, 3 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                request = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                # Never log headers, keys, URLs containing credentials, or response bodies.
                time.sleep(5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))


def fetch_charts(client, currency, days, daily=False):
    path = DATA_DIR / f'charts-{currency}-{days}.json'
    old = read_json(path) or {}
    previous = old.get('coins', {})
    result = dict(previous)
    today = datetime.now(timezone.utc).date().isoformat()
    for coin in COINS:
        existing = previous.get(coin, {})
        if (daily and str(existing.get('fetched_at', '')).startswith(today)
                and len(valid_prices(existing.get('prices'))) >= 2):
            continue
        try:
            raw = client.get(f'coins/{coin}/market_chart', vs_currency=currency, days=days)
            if not isinstance(raw, dict):
                raise ValueError('Invalid chart response')
            prices = valid_prices(raw.get('prices'))
            if len(prices) < 2:
                raise ValueError('Incomplete chart')
            result[coin] = {'prices': prices, 'fetched_at': now_iso()}
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
            print(f'::warning::Chart {coin}/{currency}/{days} unavailable ({type(error).__name__}); keeping any cached data')
    write_json(path, {'days': days, 'currency': currency, 'coins': result})
    if days == 30:
        weekly = {coin: {'prices': slice_prices(data.get('prices', []), 7),
                         'fetched_at': data.get('fetched_at')}
                  for coin, data in result.items()}
        write_json(DATA_DIR / f'charts-{currency}-7.json',
                   {'days': 7, 'currency': currency, 'coins': weekly})


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get('COINGECKO_API_KEY', '').strip()
    if not key:
        print('API key not configured; publishing reports and news only')
        return
    client = CoinGecko(key, os.environ.get('COINGECKO_PLAN', 'demo').lower() == 'pro')
    for currency in CURRENCIES:
        try:
            markets = client.get('coins/markets', vs_currency=currency,
                                 ids=','.join(COINS), sparkline='false')
            if not isinstance(markets, list) or not set(COINS).issubset({x.get('id') for x in markets if isinstance(x, dict)}):
                raise ValueError('Incomplete market snapshot')
            write_json(DATA_DIR / f'markets-{currency}.json',
                       {'fetched_at': now_iso(), 'coins': markets})
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            print(f'::warning::Market {currency} unavailable ({type(error).__name__}); keeping cached data')
        fetch_charts(client, currency, 1)
        fetch_charts(client, currency, 30, daily=True)
        fetch_charts(client, currency, 365, daily=True)


if __name__ == '__main__':
    main()
