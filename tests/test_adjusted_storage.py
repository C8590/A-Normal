from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ashare_alpha.adjusted import (
    AdjustedBuildSummary,
    AdjustedDailyBarRecord,
    save_adjusted_daily_bar_csv,
    save_adjusted_report_md,
    save_adjusted_summary_json,
    save_adjusted_validation_json,
    validate_adjusted_records,
)


def test_adjusted_storage_writes_expected_files(tmp_path: Path) -> None:
    record = AdjustedDailyBarRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        adj_type="raw",
        raw_open=10,
        raw_high=10.5,
        raw_low=9.8,
        raw_close=10.2,
        raw_pre_close=10,
        volume=1000,
        amount=10000,
        adjustment_ratio=1.0,
        adj_open=10,
        adj_high=10.5,
        adj_low=9.8,
        adj_close=10.2,
        adj_pre_close=10,
        is_adjusted=False,
        is_valid=True,
        quality_flags=[],
        quality_reason="ok",
    )
    summary = AdjustedBuildSummary(
        trade_date=date(2026, 3, 20),
        adj_type="raw",
        total_records=1,
        adjusted_records=0,
        invalid_records=0,
        missing_factor_count=0,
        stale_factor_count=0,
        summary="ok",
    )
    validation = validate_adjusted_records([record])

    save_adjusted_daily_bar_csv([record], tmp_path / "adjusted_daily_bar.csv")
    save_adjusted_summary_json(summary, tmp_path / "adjusted_summary.json")
    save_adjusted_validation_json(validation, tmp_path / "adjusted_validation.json")
    save_adjusted_report_md(summary, validation, tmp_path / "adjusted_report.md")

    assert (tmp_path / "adjusted_daily_bar.csv").exists()
    assert json.loads((tmp_path / "adjusted_summary.json").read_text(encoding="utf-8"))["total_records"] == 1
    assert "不代表交易所官方复权" in (tmp_path / "adjusted_report.md").read_text(encoding="utf-8")
