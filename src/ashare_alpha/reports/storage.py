from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ashare_alpha.reports.models import (
    BacktestResearchReport,
    BacktestSymbolSummary,
    DailyResearchReport,
    ReportStockItem,
)
from ashare_alpha.reports.renderers import (
    render_backtest_report_markdown,
    render_daily_report_markdown,
    report_to_json_dict,
)


def save_daily_report(report: DailyResearchReport, output_dir: Path | None = None) -> dict[str, Path]:
    target_dir = output_dir or Path("outputs") / "reports" / f"daily_{report.report_date.isoformat()}"
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": target_dir / "daily_report.md",
        "json": target_dir / "daily_report.json",
        "buy_candidates": target_dir / "buy_candidates.csv",
        "watch_candidates": target_dir / "watch_candidates.csv",
        "blocked_stocks": target_dir / "blocked_stocks.csv",
        "high_risk_stocks": target_dir / "high_risk_stocks.csv",
        "event_risk_stocks": target_dir / "event_risk_stocks.csv",
    }
    paths["markdown"].write_text(render_daily_report_markdown(report), encoding="utf-8")
    _write_json(report, paths["json"])
    _write_stock_items(report.buy_candidates, paths["buy_candidates"])
    _write_stock_items(report.watch_candidates, paths["watch_candidates"])
    _write_stock_items(report.blocked_stocks, paths["blocked_stocks"])
    _write_stock_items(report.high_risk_stocks, paths["high_risk_stocks"])
    _write_stock_items(report.recent_event_risk_stocks, paths["event_risk_stocks"])
    return paths


def save_backtest_report(report: BacktestResearchReport, output_dir: Path | None = None) -> dict[str, Path]:
    target_dir = output_dir or Path("outputs") / "reports" / (
        f"backtest_{report.start_date.isoformat()}_{report.end_date.isoformat()}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": target_dir / "backtest_report.md",
        "json": target_dir / "backtest_report.json",
        "symbol_summary": target_dir / "symbol_summary.csv",
        "reject_reasons": target_dir / "reject_reasons.csv",
    }
    paths["markdown"].write_text(render_backtest_report_markdown(report), encoding="utf-8")
    _write_json(report, paths["json"])
    _write_model_rows(report.trade_summary_by_symbol, paths["symbol_summary"], list(BacktestSymbolSummary.model_fields))
    _write_reject_reasons(report.top_reject_reasons, paths["reject_reasons"])
    return paths


def _write_json(report: DailyResearchReport | BacktestResearchReport, path: Path) -> None:
    path.write_text(json.dumps(report_to_json_dict(report), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_stock_items(items: list[ReportStockItem], path: Path) -> None:
    _write_model_rows(items, path, list(ReportStockItem.model_fields))


def _write_model_rows(rows: list[BaseModel], path: Path, fieldnames: list[str] | None = None) -> None:
    fieldnames = fieldnames or (list(rows[0].model_fields) if rows else [])
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.DictWriter(stream, fieldnames=fieldnames).writeheader()
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.model_dump().items()})


def _write_reject_reasons(reason_counts: dict[str, int], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["reject_reason", "count"])
        writer.writeheader()
        for reason, count in reason_counts.items():
            writer.writerow({"reject_reason": reason, "count": count})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value
