from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.audit import LeakageAuditor
from ashare_alpha.data import AnnouncementEvent, FinancialSummary, LocalCsvAdapter


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_sample_data_generates_leakage_audit_report() -> None:
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_for_date(date(2026, 3, 20))

    assert report.passed is True
    assert report.total_issues > 0
    assert report.error_count == 0


def test_publish_date_before_report_date_generates_error() -> None:
    item = FinancialSummary.model_construct(
        report_date=date(2025, 12, 31),
        publish_date=date(2025, 12, 30),
        ts_code="600001.SH",
    )
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=[],
        daily_bars=[],
        financial_summary=[item],
        announcement_events=[],
    )

    assert report.passed is False
    assert any(issue.issue_type == "financial_publish_before_report" for issue in report.issues)


def test_not_yet_published_financial_data_generates_warning() -> None:
    item = FinancialSummary(report_date="2025-12-31", publish_date="2026-03-25", ts_code="600001.SH")
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=[],
        daily_bars=[],
        financial_summary=[item],
        announcement_events=[],
    )

    assert any(issue.issue_type == "financial_not_yet_available" for issue in report.issues)


def test_future_announcement_event_generates_info() -> None:
    event = AnnouncementEvent(
        event_time="2026-03-21T09:30:00",
        ts_code="600001.SH",
        title="公告",
        source="sample",
        event_type="buyback",
        event_direction="positive",
        event_strength=0.5,
        event_risk_level="low",
    )
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=[],
        daily_bars=[],
        financial_summary=[],
        announcement_events=[event],
    )

    assert any(issue.issue_type == "announcement_future_event" for issue in report.issues)


def test_stock_master_current_state_generates_warning() -> None:
    adapter = LocalCsvAdapter(DATA_DIR)
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=adapter.load_stock_master(),
        daily_bars=[],
        financial_summary=[],
        announcement_events=[],
    )

    assert any(issue.issue_type == "stock_master_current_state_risk" for issue in report.issues)


def test_empty_source_name_generates_error() -> None:
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR, source_name="").audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=[],
        daily_bars=[],
        financial_summary=[],
        announcement_events=[],
    )

    assert report.passed is False
    assert report.error_count == 1


def test_empty_data_version_generates_warning() -> None:
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR, data_version="").audit_records(
        audit_date=date(2026, 3, 20),
        start_date=None,
        end_date=None,
        stock_master=[],
        daily_bars=[],
        financial_summary=[],
        announcement_events=[],
    )

    assert report.passed is True
    assert any(issue.issue_type == "missing_data_version" for issue in report.issues)


def test_only_warning_info_keeps_passed_true() -> None:
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_for_date(date(2026, 3, 20))

    assert report.error_count == 0
    assert report.passed is True

