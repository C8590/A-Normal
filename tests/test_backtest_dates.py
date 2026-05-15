from __future__ import annotations

from datetime import date

from ashare_alpha.backtest import get_trading_dates, select_rebalance_dates
from tests_support import daily_bar


def test_get_trading_dates_returns_sorted_dates() -> None:
    bars = [
        daily_bar(trade_date="2026-03-22", is_trading=True),
        daily_bar(trade_date="2026-03-20", is_trading=True),
        daily_bar(trade_date="2026-03-21", is_trading=False),
    ]

    assert get_trading_dates(bars, date(2026, 3, 20), date(2026, 3, 22)) == [date(2026, 3, 20), date(2026, 3, 22)]


def test_daily_rebalance_returns_all_dates() -> None:
    dates = [date(2026, 3, 20), date(2026, 3, 23)]

    assert select_rebalance_dates(dates, "daily") == dates


def test_weekly_rebalance_returns_last_date_of_week() -> None:
    dates = [date(2026, 3, 16), date(2026, 3, 18), date(2026, 3, 20), date(2026, 3, 23)]

    assert select_rebalance_dates(dates, "weekly") == [date(2026, 3, 20), date(2026, 3, 23)]


def test_monthly_rebalance_returns_last_date_of_month() -> None:
    dates = [date(2026, 2, 27), date(2026, 3, 20), date(2026, 3, 31)]

    assert select_rebalance_dates(dates, "monthly") == [date(2026, 2, 27), date(2026, 3, 31)]
