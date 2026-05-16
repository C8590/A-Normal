from __future__ import annotations

from datetime import date

from ashare_alpha.data.realism.models import AdjustmentFactorRecord
from ashare_alpha.factors import build_price_bars
from tests.tests_support import daily_bar


def test_raw_price_source_does_not_require_adjustment_factors() -> None:
    bars = [daily_bar(trade_date="2026-03-20", close=10.0)]

    records = build_price_bars(bars, None, None, "raw")

    assert len(records) == 1
    assert records[0].price_source == "raw"
    assert records[0].adjusted_used is False
    assert records[0].close == 10.0


def test_qfq_price_source_uses_adjusted_close() -> None:
    bars = [
        daily_bar(trade_date="2026-03-19", close=10.0),
        daily_bar(trade_date="2026-03-20", close=10.0),
    ]
    factors = [
        _factor("2026-03-19", 1.0),
        _factor("2026-03-20", 2.0),
    ]

    records = build_price_bars(bars, factors, None, "qfq", date(2026, 3, 19), date(2026, 3, 20))

    assert [record.price_source for record in records] == ["qfq", "qfq"]
    assert records[0].close == 5.0
    assert records[1].close == 10.0


def test_missing_adjustment_factor_preserves_record_with_quality_flag() -> None:
    bars = [daily_bar(trade_date="2026-03-20", close=10.0)]

    records = build_price_bars(bars, [], None, "qfq")

    assert len(records) == 1
    assert records[0].close is None
    assert "MISSING_ADJ_FACTOR" in records[0].adjusted_quality_flags


def _factor(trade_date: str, adj_factor: float, adj_type: str = "qfq") -> AdjustmentFactorRecord:
    return AdjustmentFactorRecord(
        ts_code="600001.SH",
        trade_date=trade_date,
        adj_factor=adj_factor,
        adj_type=adj_type,
        source_name="pytest",
        available_at=f"{trade_date}T18:00:00",
    )
