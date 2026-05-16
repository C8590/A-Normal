from __future__ import annotations

from ashare_alpha.adjusted import AdjustedDailyBarRecord, validate_adjusted_records


def test_validation_finds_adjusted_high_below_low() -> None:
    record = AdjustedDailyBarRecord.model_construct(
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
        turnover_rate=None,
        adj_factor=1.0,
        base_adj_factor=1.0,
        adjustment_ratio=1.0,
        adj_open=10,
        adj_high=9.5,
        adj_low=10.0,
        adj_close=10.2,
        adj_pre_close=10,
        raw_return_1d=None,
        adj_return_1d=None,
        is_adjusted=True,
        is_valid=False,
        quality_flags=["INVALID_ADJUSTED_PRICE"],
        quality_reason="bad",
    )

    report = validate_adjusted_records([record])

    assert report.error_count >= 1
    assert any(issue.issue_type == "adj_high_below_low" for issue in report.issues)
