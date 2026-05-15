from __future__ import annotations

from datetime import date

import pytest

from ashare_alpha.backtest import DailyEquityRecord, SimulatedTrade, calculate_metrics


def test_total_and_annualized_return_are_correct() -> None:
    metrics = calculate_metrics(_equity([10000, 10100, 10200]), [], 10000, 252)

    assert metrics.total_return == pytest.approx(0.02)
    assert metrics.annualized_return == pytest.approx((1.02) ** (252 / 2) - 1)


def test_max_drawdown_is_correct() -> None:
    metrics = calculate_metrics(_equity([10000, 11000, 9900]), [], 10000, 252)

    assert metrics.max_drawdown == pytest.approx(-0.10)


def test_sharpe_uses_population_std() -> None:
    metrics = calculate_metrics(_equity([10000, 10100, 10100]), [], 10000, 252)

    assert metrics.sharpe > 0


def test_no_sell_trade_has_no_win_rate() -> None:
    metrics = calculate_metrics(_equity([10000, 10000]), [], 10000, 252)

    assert metrics.win_rate is None


def test_win_rate_and_average_holding_days() -> None:
    trades = [_trade(10, 2), _trade(-5, 4)]
    metrics = calculate_metrics(_equity([10000, 10000]), trades, 10000, 252)

    assert metrics.win_rate == 0.5
    assert metrics.average_holding_days == 3


def test_turnover_is_gross_trade_value_over_average_equity() -> None:
    metrics = calculate_metrics(_equity([10000, 10000]), [_trade(10, 2, gross_value=1000)], 10000, 252)

    assert metrics.turnover == pytest.approx(0.1)


def _equity(values: list[float]) -> list[DailyEquityRecord]:
    records: list[DailyEquityRecord] = []
    running_max = values[0]
    prev = values[0]
    for index, value in enumerate(values):
        running_max = max(running_max, value)
        records.append(
            DailyEquityRecord(
                trade_date=date(2026, 3, 20 + index),
                cash=value,
                market_value=0,
                total_equity=value,
                positions_count=0,
                gross_exposure=0,
                daily_return=value / prev - 1 if index else 0,
                drawdown=value / running_max - 1,
            )
        )
        prev = value
    return records


def _trade(pnl: float, holding_days: int, gross_value: float = 100) -> SimulatedTrade:
    return SimulatedTrade(
        decision_date=date(2026, 3, 19),
        execution_date=date(2026, 3, 20),
        ts_code="600001.SH",
        side="SELL",
        requested_shares=100,
        filled_shares=100,
        price=10,
        gross_value=gross_value,
        commission=0.1,
        stamp_tax=0.5,
        transfer_fee=0,
        total_fee=0.6,
        net_cash_change=999.4,
        status="FILLED",
        reject_reason=None,
        realized_pnl=pnl,
        holding_days=holding_days,
        reason="测试成交",
    )
