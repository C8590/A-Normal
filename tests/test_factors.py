from __future__ import annotations

from datetime import date, timedelta
from math import isclose

from a_normal.config import TradingRulesConfig
from a_normal.data import DailyBar
from a_normal.factors import build_factor_daily, save_factor_daily_csv


def test_build_factor_daily_calculates_price_liquidity_and_volatility_factors():
    bars = make_linear_bars("000001.SZ", date(2026, 1, 1), days=61)

    factors = build_factor_daily(bars, as_of_date=date(2026, 3, 2), trading_rules=TradingRulesConfig())

    assert len(factors) == 1
    factor = factors[0]
    assert factor.ts_code == "000001.SZ"
    assert isclose(factor.momentum_5d, 160 / 155 - 1)
    assert isclose(factor.momentum_20d, 160 / 140 - 1)
    assert isclose(factor.momentum_60d, 160 / 100 - 1)
    assert factor.volatility_20d is not None
    assert factor.volatility_20d >= 0
    assert factor.max_drawdown_20d == 0
    assert factor.amount_mean_20d == 1050.5
    assert factor.turnover_mean_20d == 0.1005
    assert factor.close_above_ma20 is True
    assert factor.close_above_ma60 is True
    assert factor.limit_up_recent_count == 0
    assert factor.limit_down_recent_count == 0


def test_limit_up_and_limit_down_recent_counts_use_trading_rule_threshold():
    closes = [100, 110, 99, 108.9, 98.01]
    bars = [
        bar("000001.SZ", date(2026, 1, 1) + timedelta(days=index), close)
        for index, close in enumerate(closes)
    ]

    factors = build_factor_daily(
        bars,
        as_of_date=date(2026, 1, 5),
        trading_rules=TradingRulesConfig(normal_limit_pct=0.10),
    )

    assert factors[0].limit_up_recent_count == 2
    assert factors[0].limit_down_recent_count == 2


def test_missing_history_is_safe_and_does_not_stop_other_symbols():
    sparse = [bar("000001.SZ", date(2026, 1, 1), 10)]
    complete = make_linear_bars("000002.SZ", date(2026, 1, 1), days=21)

    factors = build_factor_daily(
        [*sparse, *complete],
        as_of_date=date(2026, 1, 21),
        trading_rules=TradingRulesConfig(),
    )
    rows = {item.ts_code: item for item in factors}

    assert "000002.SZ" in rows
    assert "000001.SZ" not in rows
    assert rows["000002.SZ"].momentum_20d is not None
    assert rows["000002.SZ"].momentum_60d is None


def test_factor_daily_results_can_be_saved_as_csv(tmp_path):
    factors = build_factor_daily(
        make_linear_bars("000001.SZ", date(2026, 1, 1), days=21),
        as_of_date=date(2026, 1, 21),
        trading_rules=TradingRulesConfig(),
    )
    output_path = tmp_path / "factor_daily.csv"

    save_factor_daily_csv(factors, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content.splitlines()[0].startswith("ts_code,trade_date,close,momentum_5d")
    assert "000001.SZ" in content


def make_linear_bars(stock_code: str, start: date, days: int) -> list[DailyBar]:
    return [
        bar(
            stock_code=stock_code,
            trade_date=start + timedelta(days=index),
            close=100 + index,
            amount=1000 + index,
            turnover_rate=0.05 + index / 1000,
        )
        for index in range(days)
    ]


def bar(
    stock_code: str,
    trade_date: date,
    close: float,
    amount: float = 1000,
    turnover_rate: float | None = 0.05,
) -> DailyBar:
    return DailyBar(
        stock_code=stock_code,
        trade_date=trade_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
        amount=amount,
        turnover_rate=turnover_rate,
    )
