from __future__ import annotations

from datetime import date, timedelta

import pytest

from ashare_alpha.data import DailyBar
from ashare_alpha.factors.limit import limit_down_count, limit_up_count
from ashare_alpha.factors.liquidity import amount_mean, turnover_mean
from ashare_alpha.factors.price import momentum, moving_average, simple_return
from ashare_alpha.factors.volatility import max_drawdown, volatility


def make_bar(index: int, close: float, turnover_rate: float | None = 1.0) -> DailyBar:
    trade_date = date(2026, 1, 1) + timedelta(days=index)
    return DailyBar(
        trade_date=trade_date,
        ts_code="600001.SH",
        open=close,
        high=close,
        low=close,
        close=close,
        pre_close=close - 1 if index else close,
        volume=1000,
        amount=close * 1000,
        turnover_rate=turnover_rate,
        limit_up=close + 1,
        limit_down=close - 1,
        is_trading=True,
    )


def test_return_1d_calculation() -> None:
    assert simple_return(110, 100) == pytest.approx(0.1)


def test_momentum_calculations() -> None:
    closes = [float(index) for index in range(1, 62)]

    assert momentum(closes, 5) == closes[-1] / closes[-6] - 1
    assert momentum(closes, 20) == closes[-1] / closes[-21] - 1
    assert momentum(closes, 60) == closes[-1] / closes[-61] - 1


def test_moving_average_and_close_above_ma() -> None:
    closes = [float(index) for index in range(1, 62)]
    ma20 = moving_average(closes, 20)
    ma60 = moving_average(closes, 60)

    assert ma20 == sum(closes[-20:]) / 20
    assert ma60 == sum(closes[-60:]) / 60
    assert closes[-1] > ma20
    assert closes[-1] > ma60


def test_volatility_uses_population_standard_deviation() -> None:
    closes = [100, 101, 99, 102, 104, 103, 105, 106, 104, 107, 109, 108, 110, 111, 109, 112, 114, 113, 115, 116, 118]
    returns = [current / previous - 1 for previous, current in zip(closes, closes[1:])]
    mean = sum(returns) / len(returns)
    expected = (sum((value - mean) ** 2 for value in returns) / len(returns)) ** 0.5

    assert volatility([float(value) for value in closes], 20) == expected


def test_max_drawdown_is_zero_or_negative() -> None:
    closes = [10, 12, 11, 13, 9]

    result = max_drawdown([float(value) for value in closes], 5)

    assert result == 9 / 13 - 1
    assert result <= 0


def test_liquidity_means() -> None:
    bars = [make_bar(index, close=10 + index, turnover_rate=1.0 if index % 2 == 0 else None) for index in range(20)]

    assert amount_mean(bars, 20) == sum(bar.amount for bar in bars) / 20
    assert turnover_mean(bars, 20) == 1.0


def test_limit_counts_use_half_tick_tolerance() -> None:
    bars = [make_bar(index, close=10) for index in range(20)]
    bars[-1] = bars[-1].model_copy(update={"close": 10.995, "limit_up": 11.0})
    bars[-2] = bars[-2].model_copy(update={"close": 9.005, "limit_down": 9.0})

    assert limit_up_count(bars, 20, price_tick=0.01) == 1
    assert limit_down_count(bars, 20, price_tick=0.01) == 1
