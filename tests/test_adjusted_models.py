from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.adjusted import AdjustedDailyBarRecord


def test_adjusted_daily_bar_record_validates_normal_record() -> None:
    record = AdjustedDailyBarRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        adj_type="qfq",
        raw_open=10,
        raw_high=10.5,
        raw_low=9.8,
        raw_close=10.2,
        raw_pre_close=10,
        volume=1000,
        amount=10000,
        turnover_rate=1.0,
        adj_factor=1.02,
        base_adj_factor=1.02,
        adjustment_ratio=1.0,
        adj_open=10,
        adj_high=10.5,
        adj_low=9.8,
        adj_close=10.2,
        adj_pre_close=10,
        raw_return_1d=0.02,
        adj_return_1d=0.02,
        is_adjusted=True,
        is_valid=True,
        quality_flags=[],
        quality_reason="ok",
    )

    assert record.adj_close == 10.2


def test_adjusted_daily_bar_record_rejects_invalid_adj_type() -> None:
    with pytest.raises(ValidationError):
        AdjustedDailyBarRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            adj_type="bad",
            raw_open=10,
            raw_high=10.5,
            raw_low=9.8,
            raw_close=10.2,
            raw_pre_close=10,
            volume=1000,
            amount=10000,
            is_adjusted=True,
            is_valid=True,
            quality_flags=[],
            quality_reason="ok",
        )


def test_adjusted_daily_bar_record_rejects_nonpositive_factor() -> None:
    with pytest.raises(ValidationError):
        AdjustedDailyBarRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            adj_type="qfq",
            raw_open=10,
            raw_high=10.5,
            raw_low=9.8,
            raw_close=10.2,
            raw_pre_close=10,
            volume=1000,
            amount=10000,
            adj_factor=0,
            is_adjusted=True,
            is_valid=False,
            quality_flags=["INVALID_ADJ_FACTOR"],
            quality_reason="bad",
        )
