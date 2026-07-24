import requests
from bs4 import BeautifulSoup
from datetime import date

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://klse.i3investor.com/',
}


def _parse_table(soup, action_type_label):
    """Parse a standard HTML table from i3investor and return rows."""
    results = []
    for row in soup.select('table tbody tr'):
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        results.append({
            'stock_code': cols[0].get_text(strip=True),
            'company':    cols[1].get_text(strip=True) if len(cols) > 1 else '—',
            'exchange':   'Bursa Malaysia',
            'ex_date':    cols[2].get_text(strip=True) if len(cols) > 2 else '—',
            'action_type': action_type_label,
            'details':    cols[3].get_text(strip=True)[:120] if len(cols) > 3 else '—',
            'market':     'Bursa',
        })
    return results


def _fetch_dividends_i3(date_from: str, date_to: str) -> list[dict]:
    """Fetch upcoming Bursa dividends from klse.i3investor.com."""
    url = (
        f'https://klse.i3investor.com/web/dividend/result_listing'
        f'?exDateFrom={date_from}&exDateTo={date_to}&sortField=exDate&sortOrder=asc&perPage=100&page=1'
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')

    results = []
    for row in soup.select('table tbody tr'):
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
        # i3investor dividend table: Code | Name | Ex-Date | Type | Amount
        div_type = cols[3].get_text(strip=True) if len(cols) > 3 else 'Dividend'
        amount   = cols[4].get_text(strip=True) if len(cols) > 4 else '—'
        results.append({
            'stock_code':  cols[0].get_text(strip=True),
            'company':     cols[1].get_text(strip=True),
            'exchange':    'Bursa Malaysia',
            'ex_date':     cols[2].get_text(strip=True),
            'action_type': div_type or 'Dividend',
            'details':     amount,
            'market':      'Bursa',
        })
    return results


def _fetch_corp_actions_i3(date_from: str, date_to: str) -> list[dict]:
    """Fetch Bursa bonus/split/consolidation from klse.i3investor.com."""
    results = []
    categories = [
        ('bonus',  'Bonus Issue'),
        ('split',  'Stock Split'),
        ('rights', 'Rights Issue'),
    ]
    for cat, label in categories:
        url = (
            f'https://klse.i3investor.com/web/announcement/result_listing'
            f'?cat={cat}&fromDate={date_from}&toDate={date_to}&perPage=100&page=1'
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            rows = _parse_table(soup, label)
            results.extend(rows)
        except Exception:
            continue
    return results


def get_dividends(trading_days: list[date]) -> list[dict]:
    if not trading_days:
        return []
    date_from = trading_days[0].strftime('%Y-%m-%d')
    date_to   = trading_days[-1].strftime('%Y-%m-%d')
    try:
        rows = _fetch_dividends_i3(date_from, date_to)
        if rows:
            return rows
        return [{'stock_code': '—', 'company': 'No upcoming dividends found for this period.',
                 'exchange': 'Bursa Malaysia', 'ex_date': '—', 'action_type': '—', 'details': '', 'market': 'Bursa'}]
    except Exception as e:
        return [{'stock_code': '—', 'company': f'Error: {e}',
                 'exchange': 'Bursa Malaysia', 'ex_date': '—', 'action_type': '—',
                 'details': 'Could not reach data source.', 'market': 'Bursa'}]


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    if not trading_days:
        return []
    date_from = trading_days[0].strftime('%Y-%m-%d')
    date_to   = trading_days[-1].strftime('%Y-%m-%d')
    try:
        rows = _fetch_corp_actions_i3(date_from, date_to)
        if rows:
            return rows
        return [{'stock_code': '—', 'company': 'No corporate actions found for this date.',
                 'exchange': 'Bursa Malaysia', 'ex_date': '—', 'action_type': '—', 'details': '', 'market': 'Bursa'}]
    except Exception as e:
        return [{'stock_code': '—', 'company': f'Error: {e}',
                 'exchange': 'Bursa Malaysia', 'ex_date': '—', 'action_type': '—',
                 'details': 'Could not reach data source.', 'market': 'Bursa'}]
