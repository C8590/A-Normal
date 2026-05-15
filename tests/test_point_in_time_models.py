from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.audit import DataAvailabilityRecord, DataSnapshot, LeakageAuditReport, LeakageIssue


def test_data_availability_record_validates() -> None:
    record = DataAvailabilityRecord(
        dataset_name="daily_bar",
        ts_code="600001.SH",
        data_date=date(2026, 3, 20),
        publish_time=None,
        available_at=datetime(2026, 3, 20, 15, 30),
        source_name="local_csv",
        data_version="sample",
        row_id="daily_bar:600001.SH:2026-03-20",
        metadata={"field": "close"},
    )

    assert record.available_at.isoformat() == "2026-03-20T15:30:00"


def test_leakage_issue_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        LeakageIssue(
            severity="critical",
            issue_type="bad",
            dataset_name="daily_bar",
            message="bad",
            recommendation="fix",
        )


def test_leakage_audit_report_counts_validate() -> None:
    issue = LeakageIssue(
        severity="warning",
        issue_type="stock_master_current_state_risk",
        dataset_name="stock_master",
        message="当前状态字段可能覆盖历史状态。",
        recommendation="使用历史状态表。",
    )
    report = LeakageAuditReport(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        generated_at=datetime(2026, 3, 20, 16, 0),
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        source_name="local_csv",
        data_version="sample",
        total_issues=1,
        error_count=0,
        warning_count=1,
        info_count=0,
        issues=[issue],
        passed=True,
        summary="ok",
    )

    assert report.warning_count == 1


def test_data_snapshot_serializes_datetime() -> None:
    snapshot = DataSnapshot(
        snapshot_id="snapshot",
        created_at=datetime(2026, 3, 20, 16, 0),
        source_name="local_csv",
        data_version="sample",
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        row_counts={"daily_bar": 1},
        min_dates={"daily_bar": "2026-03-20"},
        max_dates={"daily_bar": "2026-03-20"},
        notes=None,
    )
    payload = snapshot.model_dump(mode="json")

    assert payload["created_at"] == "2026-03-20T16:00:00"

