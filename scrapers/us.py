import requests
from datetime import date

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nasdaq.com',
    'Referer': 'https://www.nasdaq.com/',
}


def _determine_action_type(ratio: str) -> str:
    """Detect split vs reverse split from ratio string (handles '2 for 1', '1:5', etc.)."""
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
    url = f'https://api.nasdaq.com/api/calendar/splits?date={date_str}'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get('data', {}).get('rows', []) or []
    results = []
    for row in rows:
        ratio = row.get('ratio', '')
        results.append({
            'stock_code': row.get('symbol', '—'),
            'company': row.get('name', '—'),
            'exchange': row.get('exchange', 'US'),
            'ex_date': date_str,
            'action_type': _determine_action_type(ratio),
            'details': f'Ratio: {ratio}',
            'market': 'US',
        })
    return results


def _get_nasdaq_name_changes(date_str: str) -> list[dict]:
    url = (
        f'https://efts.sec.gov/LATEST/search-index?q=%22name+change%22&dateRange=custom'
        f'&startdt={date_str}&enddt={date_str}&forms=8-K'
    )
    try:
        resp = requests.get(url, headers={**HEADERS, 'Referer': 'https://efts.sec.gov/'}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get('hits', {}).get('hits', [])
        results = []
        for hit in hits[:50]:
            src = hit.get('_source', {})
            results.append({
                'stock_code': '—',
                'company': src.get('entity_name', '—'),
                'exchange': 'US',
                'ex_date': src.get('period_of_report', date_str),
                'action_type': 'Name Change',
                'details': f'Filed: {src.get("file_date", date_str)}',
                'market': 'US',
            })
        return results
    except Exception:
        return []


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    results = []
    if not trading_days:
        return results
    for d in trading_days:
        date_str = d.strftime('%Y-%m-%d')
        try:
            results.extend(_get_nasdaq_splits(date_str))
        except Exception as e:
            results.append({
                'stock_code': '—',
                'company': f'Error fetching US splits for {date_str}: {e}',
                'exchange': 'US',
                'ex_date': date_str,
                'action_type': 'Stock Split',
                'details': 'Check scrapers/us.py',
                'market': 'US',
            })
        results.extend(_get_nasdaq_name_changes(date_str))
    return results
