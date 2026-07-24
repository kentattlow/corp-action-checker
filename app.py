from flask import Flask, render_template, jsonify
from datetime import datetime, date
import pytz

from utils.trading_days import get_trading_days_from, next_trading_day
from scrapers.bursa import get_dividends, get_corporate_actions as bursa_corp
from scrapers.sgx import get_corporate_actions as sgx_corp
from scrapers.us import get_corporate_actions as us_corp

app = Flask(__name__)

MY_TZ = pytz.timezone('Asia/Kuala_Lumpur')


def today_my() -> date:
    return datetime.now(MY_TZ).date()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/refresh')
def refresh():
    today = today_my()

    # Part A: Bursa dividends — today + next 5 trading days (6 total)
    part_a_days = get_trading_days_from(today, 'MY', 6)

    # Part B dates
    part_b_my_day = next_trading_day(today, 'MY')
    part_b_sg_day = next_trading_day(today, 'SG')
    part_b_us_day = today  # Use Malaysia local date for US lookup

    data = {
        'timestamp': datetime.now(MY_TZ).strftime('%d %b %Y  %H:%M:%S'),
        'part_a': {
            'dates': [d.strftime('%d %b %Y') for d in part_a_days],
            'rows': get_dividends(part_a_days),
        },
        'part_b_my': {
            'date': part_b_my_day.strftime('%d %b %Y'),
            'rows': bursa_corp([part_b_my_day]),
        },
        'part_b_sg': {
            'date': part_b_sg_day.strftime('%d %b %Y'),
            'rows': sgx_corp([part_b_sg_day]),
        },
        'part_b_us': {
            'date': part_b_us_day.strftime('%d %b %Y'),
            'rows': us_corp([part_b_us_day]),
        },
    }
    return jsonify(data)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    print('\n  Corporate Action Monitoring is running.')
    print(f'  Open your browser and go to:  http://localhost:{port}\n')
    app.run(debug=False, host='0.0.0.0', port=port)
