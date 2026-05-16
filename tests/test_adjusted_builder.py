from __future__ import annotations

from datetime import date

import pytest

from ashare_alpha.adjusted import AdjustedDailyBarBuilder
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord
from tests.tests_support import daily_bar


def _factor(ts_code: str, trade_date: str, adj_factor: float, adj_type: str = "qfq") -> AdjustmentFactorRecord:
    return AdjustmentFactorRecord(
        ts_code=ts_code,
        trade_date=trade_date,
        adj_factor=adj_factor,
        adj_type=adj_type,
        available_at=f"{trade_date}T18:00:00",
    )


def test_raw_mode_does_not_need_factor() -> None:
    builder = AdjustedDailyBarBuilder([daily_bar()], [], adj_type="raw")

    records, summary = builder.build_for_date(date(2026, 3, 20))

    assert summary.total_records == 1
    assert records[0].adj_close == records[0].raw_close
    assert records[0].is_valid
    assert not records[0].is_adjusted


def test_qfq_mode_generates_adjusted_close() -> None:
    bars = [
        daily_bar(trade_date="2026-03-19", close=10, pre_close=9.8),
        daily_bar(trade_date="2026-03-20", open=11.8, high=12.2, low=11.7, close=12, pre_close=10),
    ]
    factors = [_factor("600001.SH", "2026-03-19", 1.0), _factor("600001.SH", "2026-03-20", 1.2)]
    builder = AdjustedDailyBarBuilder(bars, factors, adj_type="qfq")

    records, _ = builder.build_for_range(date(2026, 3, 19), date(2026, 3, 20))

    assert records[0].adj_close == pytest.approx(10 / 1.2)
    assert records[1].adj_close == pytest.approx(12)
    assert records[1].adj_return_1d == pytest.approx(12 / (10 / 1.2) - 1)


def test_hfq_mode_generates_adjusted_close_with_first_factor_base() -> None:
    bars = [
        daily_bar(trade_date="2026-03-19", close=10),
        daily_bar(trade_date="2026-03-20", open=11.8, high=12.2, low=11.7, close=12),
    ]
    factors = [
        _factor("600001.SH", "2026-03-19", 1.0, "hfq"),
        _factor("600001.SH", "2026-03-20", 1.2, "hfq"),
    ]
    builder = AdjustedDailyBarBuilder(bars, factors, adj_type="hfq")

    records, _ = builder.build_for_range(date(2026, 3, 19), date(2026, 3, 20))

    assert records[0].adj_close == pytest.approx(10)
    assert records[1].adj_close == pytest.approx(14.4)


def test_missing_factor_marks_record_invalid() -> None:
    builder = AdjustedDailyBarBuilder([daily_bar()], [], adj_type="qfq")

    records, summary = builder.build_for_date(date(2026, 3, 20))

    assert not records[0].is_valid
    assert "MISSING_ADJ_FACTOR" in records[0].quality_flags
    assert summary.missing_factor_count == 1


def test_records_are_sorted_by_ts_code_and_date() -> None:
    bars = [
        daily_bar(ts_code="600002.SH", trade_date="2026-03-20"),
        daily_bar(ts_code="600001.SH", trade_date="2026-03-20"),
        daily_bar(ts_code="600001.SH", trade_date="2026-03-19"),
    ]
    factors = [
        _factor("600001.SH", "2026-03-19", 1),
        _factor("600001.SH", "2026-03-20", 1),
        _factor("600002.SH", "2026-03-20", 1),
    ]
    builder = AdjustedDailyBarBuilder(bars, factors, adj_type="qfq")

    records, _ = builder.build_for_range(date(2026, 3, 19), date(2026, 3, 20))

    assert [(item.ts_code, item.trade_date.isoformat()) for item in records] == [
        ("600001.SH", "2026-03-19"),
        ("600001.SH", "2026-03-20"),
        ("600002.SH", "2026-03-20"),
    ]


def test_corporate_action_mismatch_adds_warning_flag() -> None:
    bars = [daily_bar(trade_date="2026-03-20")]
    factors = [_factor("600001.SH", "2026-03-20", 1.0)]
    actions = [CorporateActionRecord(ts_code="600001.SH", action_date="2026-03-20", action_type="dividend")]
    builder = AdjustedDailyBarBuilder(bars, factors, actions, adj_type="qfq")

    records, _ = builder.build_for_date(date(2026, 3, 20))

    assert "CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE" in records[0].quality_flags
