from __future__ import annotations

import hashlib
from datetime import date, datetime, time
from pathlib import Path

from ashare_alpha.audit.models import DataSnapshot
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster


def infer_available_at_for_daily_bar(bar: DailyBar) -> datetime:
    return datetime.combine(bar.trade_date, time(15, 30))


def infer_available_at_for_financial_summary(item: FinancialSummary) -> datetime:
    return datetime.combine(item.publish_date, time(0, 0))


def infer_available_at_for_announcement_event(event: AnnouncementEvent) -> datetime:
    return event.event_time


def is_record_available_for_decision(available_at: datetime, decision_time: datetime) -> bool:
    return available_at <= decision_time


def make_decision_time(trade_date: date, timing: str = "after_close") -> datetime:
    if timing == "after_close":
        return datetime.combine(trade_date, time(15, 30))
    if timing == "before_open":
        return datetime.combine(trade_date, time(9, 0))
    raise ValueError("timing must be after_close or before_open")


def build_data_snapshot(
    data_dir: Path,
    config_dir: Path,
    source_name: str,
    data_version: str,
    stock_master: list[StockMaster],
    daily_bars: list[DailyBar],
    financial_summary: list[FinancialSummary],
    announcement_events: list[AnnouncementEvent],
    notes: str | None = None,
) -> DataSnapshot:
    created_at = datetime.now()
    snapshot_seed = f"{source_name}|{data_version}|{created_at.isoformat()}|{data_dir}|{config_dir}"
    snapshot_id = hashlib.sha256(snapshot_seed.encode("utf-8")).hexdigest()[:16]
    row_counts = {
        "stock_master": len(stock_master),
        "daily_bar": len(daily_bars),
        "financial_summary": len(financial_summary),
        "announcement_event": len(announcement_events),
    }
    min_dates = {
        "stock_master": _min_iso(stock.list_date for stock in stock_master),
        "daily_bar": _min_iso(bar.trade_date for bar in daily_bars),
        "financial_summary": _min_iso(item.report_date for item in financial_summary),
        "financial_summary_publish_date": _min_iso(item.publish_date for item in financial_summary),
        "announcement_event": _min_iso(event.event_time.date() for event in announcement_events),
    }
    max_dates = {
        "stock_master": _max_iso(stock.list_date for stock in stock_master),
        "daily_bar": _max_iso(bar.trade_date for bar in daily_bars),
        "financial_summary": _max_iso(item.report_date for item in financial_summary),
        "financial_summary_publish_date": _max_iso(item.publish_date for item in financial_summary),
        "announcement_event": _max_iso(event.event_time.date() for event in announcement_events),
    }
    return DataSnapshot(
        snapshot_id=snapshot_id,
        created_at=created_at,
        source_name=source_name,
        data_version=data_version,
        data_dir=str(data_dir),
        config_dir=str(config_dir),
        row_counts=row_counts,
        min_dates=min_dates,
        max_dates=max_dates,
        notes=notes,
    )


def _min_iso(values) -> str | None:
    materialized = list(values)
    return min(materialized).isoformat() if materialized else None


def _max_iso(values) -> str | None:
    materialized = list(values)
    return max(materialized).isoformat() if materialized else None
