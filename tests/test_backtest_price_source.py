from __future__ import annotations

from datetime import date, timedelta

import pytest

from ashare_alpha.backtest import BacktestPriceSourceProvider
from ashare_alpha.data.realism.models import AdjustmentFactorRecord
from tests.tests_support import daily_bar


def test_raw_price_source_returns_raw_execution_and_valuation() -> None:
    bar = daily_bar(trade_date="2026-01-02", open=10.0, high=11.0, close=11.0)
    provider = BacktestPriceSourceProvider([bar], price_source="raw")

    assert provider.get_execution_bar("600001.SH", date(2026, 1, 2)) == bar
    assert provider.get_raw_bar("600001.SH", date(2026, 1, 2)) == bar
    assert provider.get_valuation_price("600001.SH", date(2026, 1, 2)) == 11.0
    assert provider.get_target_position_price("600001.SH", date(2026, 1, 2)) == 10.0


def test_qfq_price_source_uses_adjusted_close_without_changing_execution_bar() -> None:
    bars = _bars()
    provider = BacktestPriceSourceProvider(bars, _factors("qfq"), price_source="qfq")

    assert provider.get_execution_bar("600001.SH", date(2026, 1, 2)) == bars[1]
    assert provider.get_valuation_price("600001.SH", date(2026, 1, 2)) == 50.0
    assert provider.get_target_position_price("600001.SH", date(2026, 1, 2)) == 50.0


def test_hfq_price_source_uses_adjusted_close_without_changing_execution_bar() -> None:
    bars = _bars()
    provider = BacktestPriceSourceProvider(bars, _factors("hfq"), price_source="hfq")

    assert provider.get_execution_bar("600001.SH", date(2026, 1, 2)) == bars[1]
    assert provider.get_valuation_price("600001.SH", date(2026, 1, 2)) == 200.0


def test_missing_adjusted_price_returns_none_and_updates_status() -> None:
    provider = BacktestPriceSourceProvider(_bars(), [], price_source="qfq")

    assert provider.get_valuation_price("600001.SH", date(2026, 1, 2)) is None
    assert provider.get_price_source_status()["missing_adjusted_count"] == 1


def test_invalid_price_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="price_source"):
        BacktestPriceSourceProvider(_bars(), price_source="bad")


def _bars():
    start = date(2026, 1, 1)
    return [
        daily_bar(
            trade_date=(start + timedelta(days=index)).isoformat(),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            pre_close=100.0,
            limit_up=110.0,
            limit_down=90.0,
        )
        for index in range(3)
    ]


def _factors(adj_type: str) -> list[AdjustmentFactorRecord]:
    factors = [1.0, 1.0, 2.0] if adj_type == "qfq" else [1.0, 2.0, 2.0]
    return [
        AdjustmentFactorRecord(
            ts_code="600001.SH",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            adj_factor=factor,
            adj_type=adj_type,
            source_name="pytest",
            available_at=f"2026-01-0{index + 1}T18:00:00",
        )
        for index, factor in enumerate(factors)
    ]
