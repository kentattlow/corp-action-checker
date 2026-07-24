from datetime import date, timedelta
import holidays


def _get_holidays(market):
    year = date.today().year
    if market == 'MY':
        return holidays.Malaysia(years=[year, year + 1])
    elif market == 'SG':
        return holidays.Singapore(years=[year, year + 1])
    elif market == 'US':
        return holidays.UnitedStates(years=[year, year + 1])
    return {}


def is_trading_day(d, market):
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in _get_holidays(market)


def next_trading_day(d, market):
    """Returns the next trading day AFTER d."""
    d = d + timedelta(days=1)
    while not is_trading_day(d, market):
        d += timedelta(days=1)
    return d


def get_trading_days_from(start, market, count):
    """Returns 'count' trading days starting from start (inclusive if trading day)."""
    days = []
    current = start
    # If start is not a trading day, move forward to the next one
    while not is_trading_day(current, market):
        current += timedelta(days=1)
    while len(days) < count:
        if is_trading_day(current, market):
            days.append(current)
        current += timedelta(days=1)
    return days
