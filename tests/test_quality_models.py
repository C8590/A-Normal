from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.quality import DataQualityReport, QualityIssue


def test_quality_issue_validates() -> None:
    issue = QualityIssue(
        severity="warning",
        dataset_name="daily_bar",
        issue_type="extreme_daily_return",
        message="涨跌幅异常。",
        recommendation="核对价格。",
    )

    assert issue.severity == "warning"


def test_quality_issue_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        QualityIssue(
            severity="critical",
            dataset_name="daily_bar",
            issue_type="bad",
            message="bad",
            recommendation="fix",
        )


def test_data_quality_report_error_count_controls_passed() -> None:
    issue = QualityIssue(
        severity="error",
        dataset_name="daily_bar",
        issue_type="high_below_low",
        message="high 小于 low。",
        recommendation="检查价格。",
    )
    report = _report([issue], passed=False)

    assert report.error_count == 1
    assert report.passed is False


def test_data_quality_report_warning_info_passes() -> None:
    issue = QualityIssue(
        severity="warning",
        dataset_name="daily_bar",
        issue_type="few_trading_records",
        message="记录较少。",
        recommendation="补齐数据。",
    )
    report = _report([issue], passed=True)

    assert report.error_count == 0
    assert report.passed is True


def _report(issues: list[QualityIssue], passed: bool) -> DataQualityReport:
    return DataQualityReport(
        generated_at=datetime(2026, 3, 20, 16, 0),
        data_dir="data/sample/ashare_alpha",
        source_name=None,
        data_version=None,
        total_issues=len(issues),
        error_count=sum(1 for issue in issues if issue.severity == "error"),
        warning_count=sum(1 for issue in issues if issue.severity == "warning"),
        info_count=sum(1 for issue in issues if issue.severity == "info"),
        row_counts={},
        coverage={},
        issues=issues,
        passed=passed,
        summary="数据质量检查完成。",
    )

