import requests
from bs4 import BeautifulSoup
from datetime import date

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.sgx.com/',
}

# SGX corporate action types we care about
SGX_ACTION_TYPES = ['Bonus Issue', 'Stock Split', 'Share Consolidation', 'Rights Issue']


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    """Part B: SGX bonus, split, reverse split for given trading days."""
    results = []
    if not trading_days:
        return results

    for d in trading_days:
        date_str = d.strftime('%Y-%m-%d')
        # SGX has a corporate actions API endpoint
        url = f'https://api.sgx.com/securities/v1.1/corporate-actions?exDate={date_str}&pageSize=100'
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            items = data.get('data', {}).get('items', [])
            for item in items:
                action_type = item.get('corporateActionType', '')
                # Filter for the action types we want
                if not any(t.lower() in action_type.lower() for t in ['bonus', 'split', 'consolidat']):
                    continue
                results.append({
                    'stock_code': item.get('stockCode', '—'),
                    'company': item.get('companyName', '—'),
                    'exchange': 'SGX',
                    'ex_date': item.get('exDate', date_str),
                    'action_type': action_type,
                    'details': item.get('remarks', '')[:120],
                    'market': 'SGX',
                })
        except Exception as e:
            results.append({
                'stock_code': '—',
                'company': f'Error fetching SGX data for {date_str}: {e}',
                'exchange': 'SGX',
                'ex_date': date_str,
                'action_type': '—',
                'details': 'Check scrapers/sgx.py',
                'market': 'SGX',
            })
    return results
