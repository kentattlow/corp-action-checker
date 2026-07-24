import requests
from datetime import date

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.sgx.com/',
    'Origin': 'https://www.sgx.com',
}

SGX_API_URLS = [
    'https://api.sgx.com/securities/v1.1/corporate-actions?exDate={date}&pageSize=100',
    'https://api2.sgx.com/sites/default/files/reports/corporate-actions/{date}.json',
]


def get_corporate_actions(trading_days: list[date]) -> list[dict]:
    results = []
    if not trading_days:
        return results

    for d in trading_days:
        date_str = d.strftime('%Y-%m-%d')
        fetched = False

        for url_template in SGX_API_URLS:
            url = url_template.format(date=date_str)
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # Try multiple response shapes
                items = (
                    data.get('data', {}).get('items', [])
                    or data.get('items', [])
                    or (data if isinstance(data, list) else [])
                )

                for item in items:
                    action_type = (
                        item.get('corporateActionType', '')
                        or item.get('actionType', '')
                        or item.get('type', '')
                    )
                    if not any(t in action_type.lower() for t in ['bonus', 'split', 'consolidat']):
                        continue
                    results.append({
                        'stock_code': item.get('stockCode', item.get('code', '—')),
                        'company': item.get('companyName', item.get('name', '—')),
                        'exchange': 'SGX',
                        'ex_date': item.get('exDate', item.get('ex_date', date_str)),
                        'action_type': action_type or '—',
                        'details': item.get('remarks', item.get('details', ''))[:120],
                        'market': 'SGX',
                    })
                fetched = True
                break
            except Exception:
                continue

        if not fetched:
            results.append({
                'stock_code': '—',
                'company': f'Unable to fetch SGX data for {date_str}',
                'exchange': 'SGX',
                'ex_date': date_str,
                'action_type': '—',
                'details': 'SGX API may have changed. No data available.',
                'market': 'SGX',
            })

    return results
