from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.realism import OptionalRealismDataLoader
from ashare_alpha.data.realism.validation import (
    check_adjustment_factor,
    check_corporate_action,
    check_stock_status_history,
    check_trade_calendar,
)
from ashare_alpha.data.validation import DataValidationError
from ashare_alpha.quality.checks import (
    check_announcement_event,
    check_cross_table_coverage,
    check_daily_bar,
    check_financial_summary,
    check_stock_master,
)
from ashare_alpha.quality.models import DataQualityReport, QualityIssue


class DataQualityReporter:
    def __init__(
        self,
        data_dir: Path,
        config_dir: Path,
        source_name: str | None = None,
        data_version: str | None = None,
        target_date: date | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.config_dir = Path(config_dir)
        self.source_name = source_name
        self.data_version = data_version
        self.target_date = target_date

    def run(self) -> DataQualityReport:
        adapter = LocalCsvAdapter(self.data_dir)
        validation_report = adapter.validate_all()
        stock_rows = _read_csv(self.data_dir / "stock_master.csv")
        daily_rows = _read_csv(self.data_dir / "daily_bar.csv")
        financial_rows = _read_csv(self.data_dir / "financial_summary.csv")
        announcement_rows = _read_csv(self.data_dir / "announcement_event.csv")
        trade_calendar_rows = _read_csv(self.data_dir / "trade_calendar.csv")
        stock_status_rows = _read_csv(self.data_dir / "stock_status_history.csv")
        adjustment_rows = _read_csv(self.data_dir / "adjustment_factor.csv")
        corporate_action_rows = _read_csv(self.data_dir / "corporate_action.csv")

        issues: list[QualityIssue] = []
        for error in validation_report.errors:
            issues.append(
                QualityIssue(
                    severity="error",
                    dataset_name="validation",
                    issue_type="validation_error",
                    message=error,
                    recommendation="先修复 LocalCsvAdapter 数据校验错误，再复查质量报告。",
                )
            )
        for warning in validation_report.warnings:
            issues.append(
                QualityIssue(
                    severity="warning",
                    dataset_name="validation",
                    issue_type="validation_warning",
                    message=warning,
                    recommendation="检查 LocalCsvAdapter 数据校验警告。",
                )
            )

        stock_codes = {row.get("ts_code", "").strip() for row in stock_rows if row.get("ts_code", "").strip()}
        daily_bar_max_date = _max_date(row.get("trade_date") for row in daily_rows)
        issues.extend(check_stock_master(stock_rows))
        issues.extend(check_daily_bar(daily_rows, stock_codes))
        issues.extend(check_financial_summary(financial_rows, stock_codes))
        issues.extend(check_announcement_event(announcement_rows, stock_codes, daily_bar_max_date))
        issues.extend(
            check_cross_table_coverage(
                stock_rows,
                daily_rows,
                financial_rows,
                announcement_rows,
                self.target_date,
            )
        )
        issues.extend(
            self._realism_issues(
                stock_rows=stock_rows,
                daily_rows=daily_rows,
                trade_calendar_rows=trade_calendar_rows,
                stock_status_rows=stock_status_rows,
                adjustment_rows=adjustment_rows,
                corporate_action_rows=corporate_action_rows,
            )
        )

        row_counts = {
            "stock_master": len(stock_rows),
            "daily_bar": len(daily_rows),
            "financial_summary": len(financial_rows),
            "announcement_event": len(announcement_rows),
            "trade_calendar": len(trade_calendar_rows),
            "stock_status_history": len(stock_status_rows),
            "adjustment_factor": len(adjustment_rows),
            "corporate_action": len(corporate_action_rows),
        }
        coverage = _coverage(
            stock_rows,
            daily_rows,
            financial_rows,
            announcement_rows,
            trade_calendar_rows,
            stock_status_rows,
            adjustment_rows,
            corporate_action_rows,
        )
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        info_count = sum(1 for issue in issues if issue.severity == "info")
        summary = (
            f"数据质量检查完成：error={error_count}，warning={warning_count}，info={info_count}。"
            "报告只做辅助检查，不代表数据完全正确。"
        )
        return DataQualityReport(
            generated_at=datetime.now(),
            data_dir=str(self.data_dir),
            source_name=self.source_name,
            data_version=self.data_version,
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            row_counts=row_counts,
            coverage=coverage,
            issues=issues,
            passed=error_count == 0,
            summary=summary,
        )

    def _realism_issues(
        self,
        stock_rows: list[dict[str, str]],
        daily_rows: list[dict[str, str]],
        trade_calendar_rows: list[dict[str, str]],
        stock_status_rows: list[dict[str, str]],
        adjustment_rows: list[dict[str, str]],
        corporate_action_rows: list[dict[str, str]],
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        try:
            OptionalRealismDataLoader(self.data_dir).load_all()
        except DataValidationError as exc:
            issues.append(
                QualityIssue(
                    severity="error",
                    dataset_name="realism",
                    issue_type="realism_validation_error",
                    message=str(exc),
                    recommendation="Fix optional realism CSV schema or row values before using realism checks.",
                )
            )

        if trade_calendar_rows:
            issues.extend(check_trade_calendar(trade_calendar_rows))
        if stock_status_rows:
            issues.extend(check_stock_status_history(stock_status_rows, stock_rows, self.target_date))
        if adjustment_rows:
            issues.extend(check_adjustment_factor(adjustment_rows, stock_rows, daily_rows))
        if corporate_action_rows:
            issues.extend(check_corporate_action(corporate_action_rows, stock_rows))
        return issues


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return [dict(row) for row in csv.DictReader(stream)]
    except csv.Error:
        return []


def _coverage(
    stock_rows: list[dict[str, str]],
    daily_rows: list[dict[str, str]],
    financial_rows: list[dict[str, str]],
    announcement_rows: list[dict[str, str]],
    trade_calendar_rows: list[dict[str, str]] | None = None,
    stock_status_rows: list[dict[str, str]] | None = None,
    adjustment_rows: list[dict[str, str]] | None = None,
    corporate_action_rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    daily_dates = sorted({item for item in (_parse_date(row.get("trade_date")) for row in daily_rows) if item})
    calendar_dates = sorted(
        {item for item in (_parse_date(row.get("calendar_date")) for row in trade_calendar_rows or []) if item}
    )
    return {
        "stock_count": len(stock_rows),
        "daily_bar_rows": len(daily_rows),
        "daily_bar_min_date": daily_dates[0].isoformat() if daily_dates else None,
        "daily_bar_max_date": daily_dates[-1].isoformat() if daily_dates else None,
        "financial_rows": len(financial_rows),
        "announcement_rows": len(announcement_rows),
        "stocks_with_daily_bar": len({row.get("ts_code", "").strip() for row in daily_rows if row.get("ts_code", "").strip()}),
        "stocks_with_financial_summary": len({row.get("ts_code", "").strip() for row in financial_rows if row.get("ts_code", "").strip()}),
        "stocks_with_announcement_event": len({row.get("ts_code", "").strip() for row in announcement_rows if row.get("ts_code", "").strip()}),
        "trade_calendar_min_date": calendar_dates[0].isoformat() if calendar_dates else None,
        "trade_calendar_max_date": calendar_dates[-1].isoformat() if calendar_dates else None,
        "stock_status_history_rows": len(stock_status_rows or []),
        "adjustment_factor_rows": len(adjustment_rows or []),
        "corporate_action_rows": len(corporate_action_rows or []),
    }


def _max_date(values) -> date | None:
    dates = [item for item in (_parse_date(value) for value in values) if item is not None]
    return max(dates) if dates else None


def _parse_date(value: Any) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None
