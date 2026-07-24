import re
import requests
from datetime import date

NASDAQ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.nasdaq.com',
    'Referer': 'https://www.nasdaq.com/',
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


def _parse_edgar_hit(src: dict, action_type: str, date_str: str) -> dict:
    """Parse an EDGAR hit's _source into a result row."""
    display_names = src.get('display_names', [])
    ticker = '—'
    company = '—'
    if display_names:
        dn = display_names[0]
        # Format: "Company Name  (TICKER)  (CIK 000...)"
        m = re.search(r'\(([A-Z]{1,5})\)', dn)
        if m:
            ticker = m.group(1)
        company = re.sub(r'\s*\([^)]+\)\s*', '', dn).strip()
    return {
        'stock_code':  ticker,
        'company':     company,
        'exchange':    'SEC/EDGAR',
        'ex_date':     src.get('period_ending', src.get('file_date', date_str)),
        'action_type': action_type,
        'details':     f'Filed: {src.get("file_date", date_str)}',
        'market':      'US',
    }


def _get_nasdaq_splits(date_str: str) -> list[dict]:
    """NASDAQ-listed splits and reverse splits."""
    url = f'https://api.nasdaq.com/api/calendar/splits?date={date_str}'
    resp = requests.get(url, headers=NASDAQ_HEADERS, timeout=15)
    resp.raise_for_status()
    rows = resp.json().get('data', {}).get('rows', []) or []
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


def _get_edgar_splits(date_str: str) -> list[dict]:
    """OTC and listed splits/reverse splits via SEC EDGAR 8-K filings (item 4.08 / 5.03)."""
    results = []
    for query, action_type in [
        ('%22stock+split%22+OR+%22forward+split%22', 'Stock Split'),
        ('%22reverse+split%22+OR+%22reverse+stock+split%22+OR+%22share+consolidation%22', 'Reverse Split'),
    ]:
        url = (
            f'https://efts.sec.gov/LATEST/search-index?q={query}'
            f'&forms=8-K&dateRange=custom&startdt={date_str}&enddt={date_str}'
        )
        try:
            resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
            resp.raise_for_status()
            hits = resp.json().get('hits', {}).get('hits', []) or []
            for hit in hits:
                src = hit.get('_source', {})
                # Only keep filings with item 5.03 (articles amendment) for accuracy
                items = src.get('items', [])
                if '5.03' not in items and '8.01' not in items:
                    continue
                results.append(_parse_edgar_hit(src, action_type, date_str))
        except Exception:
            continue
    return results


def _get_edgar_name_changes(date_str: str) -> list[dict]:
    """Name changes via SEC EDGAR 8-K filings with item 5.03."""
    queries = [
        '%22changed+its+name%22',
        '%22change+of+name%22',
        '%22renamed+to%22',
    ]
    results = []
    seen_ciks = set()
    for query in queries:
        url = (
            f'https://efts.sec.gov/LATEST/search-index?q={query}'
            f'&forms=8-K&dateRange=custom&startdt={date_str}&enddt={date_str}'
        )
        try:
            resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
            resp.raise_for_status()
            hits = resp.json().get('hits', {}).get('hits', []) or []
            for hit in hits:
                src = hit.get('_source', {})
                ciks = tuple(src.get('ciks', []))
                if ciks in seen_ciks:
                    continue
                seen_ciks.add(ciks)
                # Filter: item 5.03 = articles/bylaws amendment (used for name changes)
                items = src.get('items', [])
                if '5.03' not in items:
                    continue
                results.append(_parse_edgar_hit(src, 'Name Change', date_str))
        except Exception:
            continue
    return results


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    results = []
    if not trading_days:
        return results

    seen = set()

    def add(rows):
        for r in rows:
            key = (r['stock_code'], r['action_type'], r['ex_date'])
            if key not in seen:
                seen.add(key)
                results.append(r)

    for d in trading_days:
        date_str = d.strftime('%Y-%m-%d')

        # NASDAQ splits (primary source for listed stocks)
        try:
            add(_get_nasdaq_splits(date_str))
        except Exception:
            pass

        # EDGAR splits (additional coverage for OTC + listed stocks)
        try:
            add(_get_edgar_splits(date_str))
        except Exception:
            pass

        # EDGAR name changes
        try:
            add(_get_edgar_name_changes(date_str))
        except Exception:
            pass

    return results
