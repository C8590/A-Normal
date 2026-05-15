from __future__ import annotations

from ashare_alpha.probability import compute_future_return, make_win_label
from tests_support import daily_bar


def test_future_5d_return_calculates_from_trading_closes() -> None:
    bars = [_bar(day, 10 + day) for day in range(1, 8)]

    result = compute_future_return(bars, "600001.SH", bars[0].trade_date, 5)

    assert result == bars[5].close / bars[0].close - 1


def test_future_return_none_when_future_data_insufficient() -> None:
    bars = [daily_bar(trade_date=f"2026-03-{day:02d}") for day in range(1, 4)]

    assert compute_future_return(bars, "600001.SH", bars[0].trade_date, 5) is None


def test_future_return_none_when_trade_date_not_trading() -> None:
    bars = [
        daily_bar(trade_date="2026-03-01", is_trading=False),
        _bar(2, 11),
        _bar(3, 12),
    ]

    assert compute_future_return(bars, "600001.SH", bars[0].trade_date, 1) is None


def test_win_label_uses_strict_greater_than_threshold() -> None:
    assert make_win_label(0.01, 0.0) == 1
    assert make_win_label(0.0, 0.0) == 0
    assert make_win_label(None, 0.0) is None


def test_label_calculation_does_not_mutate_feature_bars() -> None:
    bars = [_bar(day, 10 + day) for day in range(1, 8)]
    before = [bar.close for bar in bars]

    compute_future_return(bars, "600001.SH", bars[0].trade_date, 5)

    assert [bar.close for bar in bars] == before


def _bar(day: int, close: float):
    return daily_bar(
        trade_date=f"2026-03-{day:02d}",
        open=close,
        high=close + 0.2,
        low=close - 0.2,
        close=close,
        pre_close=max(close - 0.1, 0.01),
    )
