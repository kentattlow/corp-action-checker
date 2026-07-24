import requests
from datetime import date

NASDAQ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nasdaq.com',
    'Referer': 'https://www.nasdaq.com/',
}

OTC_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.otcmarkets.com',
    'Referer': 'https://www.otcmarkets.com/',
}

EDGAR_HEADERS = {
    'User-Agent': 'CorporateActionMonitor contact@example.com',
    'Accept': 'application/json',
}


def _determine_action_type(ratio: str) -> str:
    r = ratio.lower().strip()
    new_s, old_s = None, None
    try:
        if ' for ' in r:
            parts = r.split(' for ')
            new_s, old_s = float(parts[0].strip()), float(parts[1].strip())
        elif ':' in r:
            parts = r.replace(' ', '').split(':')
            new_s, old_s = float(parts[0]), float(parts[1])
        elif '/' in r:
            parts = r.replace(' ', '').split('/')
            new_s, old_s = float(parts[0]), float(parts[1])
    except Exception:
        pass
    if new_s is not None and old_s is not None:
        return 'Reverse Split' if new_s < old_s else 'Stock Split'
    return 'Stock Split'


def _get_nasdaq_splits(date_str: str) -> list[dict]:
    """NASDAQ-listed stock splits."""
    url = f'https://api.nasdaq.com/api/calendar/splits?date={date_str}'
    resp = requests.get(url, headers=NASDAQ_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get('data', {}).get('rows', []) or []
    results = []
    for row in rows:
        ratio = row.get('ratio', '')
        results.append({
            'stock_code':  row.get('symbol', '—'),
            'company':     row.get('name', '—'),
            'exchange':    row.get('exchange', 'NASDAQ'),
            'ex_date':     date_str,
            'action_type': _determine_action_type(ratio),
            'details':     f'Ratio: {ratio}',
            'market':      'US',
        })
    return results


def _get_otc_splits(date_str: str) -> list[dict]:
    """OTC Markets stock splits and reverse splits."""
    url = (
        f'https://backend.otcmarkets.com/otcapi/company/corporate-actions'
        f'?fromDate={date_str}&toDate={date_str}&actionType=SPLIT&pageSize=100&pageNum=1'
    )
    resp = requests.get(url, headers=OTC_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get('records', data.get('items', data.get('data', [])))
    if isinstance(items, dict):
        items = items.get('records', items.get('items', []))
    results = []
    for item in (items or []):
        ratio = item.get('splitRatio', item.get('ratio', ''))
        ticker = item.get('symbol', item.get('ticker', '—'))
        name = item.get('companyName', item.get('name', '—'))
        results.append({
            'stock_code':  ticker,
            'company':     name,
            'exchange':    'OTC',
            'ex_date':     item.get('exDate', item.get('effectiveDate', date_str)),
            'action_type': _determine_action_type(str(ratio)) if ratio else 'Stock Split',
            'details':     f'Ratio: {ratio}' if ratio else '—',
            'market':      'US',
        })
    return results


def _get_name_changes(date_str: str) -> list[dict]:
    """Name changes via SEC EDGAR full-text search on 8-K filings."""
    url = (
        'https://efts.sec.gov/LATEST/search-index?'
        'q=%22changed+its+name%22+OR+%22change+of+name%22+OR+%22name+change%22'
        f'&forms=8-K&dateRange=custom&startdt={date_str}&enddt={date_str}'
    )
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get('hits', {}).get('hits', []) or []
    results = []
    for hit in hits[:100]:
        src = hit.get('_source', {})
        ticker = src.get('ticker_symbols', src.get('tickers', []))
        if isinstance(ticker, list):
            ticker = ticker[0] if ticker else '—'
        results.append({
            'stock_code':  ticker or '—',
            'company':     src.get('entity_name', src.get('display_names', ['—'])[0] if isinstance(src.get('display_names'), list) else '—'),
            'exchange':    'SEC/EDGAR',
            'ex_date':     src.get('period_of_report', date_str),
            'action_type': 'Name Change',
            'details':     f'Filed: {src.get("file_date", date_str)}',
            'market':      'US',
        })
    return results


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    results = []
    if not trading_days:
        return results

    seen = set()

    for d in trading_days:
        date_str = d.strftime('%Y-%m-%d')

        # NASDAQ splits
        try:
            for row in _get_nasdaq_splits(date_str):
                key = (row['stock_code'], row['action_type'], date_str)
                if key not in seen:
                    seen.add(key)
                    results.append(row)
        except Exception:
            pass

        # OTC splits
        try:
            for row in _get_otc_splits(date_str):
                key = (row['stock_code'], row['action_type'], date_str)
                if key not in seen:
                    seen.add(key)
                    results.append(row)
        except Exception:
            pass

        # Name changes via SEC EDGAR
        try:
            for row in _get_name_changes(date_str):
                key = (row['stock_code'], 'Name Change', date_str)
                if key not in seen:
                    seen.add(key)
                    results.append(row)
        except Exception:
            pass

    return results
