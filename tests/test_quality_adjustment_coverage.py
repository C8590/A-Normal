from __future__ import annotations

from pathlib import Path

from ashare_alpha.quality import DataQualityReporter


def test_quality_report_includes_adjustment_factor_coverage() -> None:
    report = DataQualityReporter(Path("data/sample/ashare_alpha"), Path("configs/ashare_alpha")).run()

    assert "adjustment_factor_coverage_rate" in report.coverage
    assert any(issue.issue_type == "missing_factor_for_trading_daily_bar" for issue in report.issues)
