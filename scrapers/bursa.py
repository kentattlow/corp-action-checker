import requests
from bs4 import BeautifulSoup
from datetime import date

ACTION_LABEL = {
    'DI': 'Dividend',
    'DE': 'Dividend Entitlement',
    'SD': 'Special Dividend',
    'FD': 'Final Dividend',
    'BD': 'Interim Dividend',
    'BI': 'Bonus Issue',
    'SS': 'Stock Split',
    'SC': 'Share Consolidation',
    'RS': 'Reverse Split',
}

DIVIDEND_TYPES = ['DI', 'DE', 'SD', 'FD', 'BD']
CORP_ACTION_TYPES = ['BI', 'SS', 'SC', 'RS']


def _make_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    # Load main page first to get Cloudflare cookies
    try:
        session.get('https://www.bursamalaysia.com/', timeout=15)
    except Exception:
        pass
    return session


def _fetch_announcements(date_from, date_to, ann_types):
    results = []
    session = _make_session()

    for ann_type in ann_types:
        url = (
            'https://www.bursamalaysia.com/market_information/announcements/company_announcement'
            f'?ann_type={ann_type}&date_from={date_from}&date_to={date_to}&per_page=100&page=1'
        )
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            rows = soup.select('table tbody tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                results.append({
                    'stock_code': cols[0].get_text(strip=True),
                    'company': cols[1].get_text(strip=True),
                    'exchange': 'Bursa Malaysia',
                    'ex_date': cols[2].get_text(strip=True),
                    'action_type': ACTION_LABEL.get(ann_type, ann_type),
                    'details': cols[3].get_text(strip=True)[:120],
                    'market': 'Bursa',
                })
        except Exception as e:
            results.append({
                'stock_code': '—',
                'company': f'Unable to fetch Bursa data ({ACTION_LABEL.get(ann_type, ann_type)}): {e}',
                'exchange': 'Bursa Malaysia',
                'ex_date': '—',
                'action_type': ACTION_LABEL.get(ann_type, ann_type),
                'details': 'Bursa website may be blocking automated access. Try refreshing.',
                'market': 'Bursa',
            })
    return results


def get_dividends(trading_days: list[date]) -> list[dict]:
    if not trading_days:
        return []
    date_from = trading_days[0].strftime('%Y-%m-%d')
    date_to = trading_days[-1].strftime('%Y-%m-%d')
    return _fetch_announcements(date_from, date_to, DIVIDEND_TYPES)


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    if not trading_days:
        return []
    date_from = trading_days[0].strftime('%Y-%m-%d')
    date_to = trading_days[-1].strftime('%Y-%m-%d')
    return _fetch_announcements(date_from, date_to, CORP_ACTION_TYPES)
