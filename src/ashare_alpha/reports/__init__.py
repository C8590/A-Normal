from __future__ import annotations

from ashare_alpha.reports.backtest_report import BacktestReportBuilder
from ashare_alpha.reports.daily_report import DailyReportBuilder
from ashare_alpha.reports.models import (
    BacktestResearchReport,
    BacktestSymbolSummary,
    DailyResearchReport,
    REPORT_DISCLAIMER,
    ReportStockItem,
)
from ashare_alpha.reports.renderers import (
    render_backtest_report_markdown,
    render_daily_report_markdown,
    report_to_json_dict,
)
from ashare_alpha.reports.storage import save_backtest_report, save_daily_report

__all__ = [
    "BacktestReportBuilder",
    "BacktestResearchReport",
    "BacktestSymbolSummary",
    "DailyResearchReport",
    "DailyReportBuilder",
    "REPORT_DISCLAIMER",
    "ReportStockItem",
    "render_backtest_report_markdown",
    "render_daily_report_markdown",
    "report_to_json_dict",
    "save_backtest_report",
    "save_daily_report",
]
