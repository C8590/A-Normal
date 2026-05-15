from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.data.realism import OptionalRealismDataLoader, TradingCalendar


def test_trading_calendar_open_dates_and_neighbors() -> None:
    bundle = OptionalRealismDataLoader(Path("data/sample/ashare_alpha")).load_all()
    calendar = TradingCalendar(bundle.trade_calendar)

    assert calendar.is_open(date(2026, 1, 2)) is True
    assert calendar.is_open(date(2026, 1, 3)) is False
    assert calendar.previous_open_date(date(2026, 1, 5)) == date(2026, 1, 2)
    assert calendar.next_open_date(date(2026, 1, 3)) == date(2026, 1, 5)
    assert len(calendar.open_dates(date(2026, 1, 1), date(2026, 1, 9))) == 6


def test_empty_trading_calendar_returns_none_or_empty() -> None:
    calendar = TradingCalendar([])

    assert calendar.is_open(date(2026, 1, 2)) is None
    assert calendar.previous_open_date(date(2026, 1, 2)) is None
    assert calendar.next_open_date(date(2026, 1, 2)) is None
    assert calendar.open_dates(date(2026, 1, 1), date(2026, 1, 9)) == []
