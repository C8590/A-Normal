from __future__ import annotations

import csv
from pathlib import Path

import pytest

from a_normal.data import (
    AnnouncementEvent,
    DailyBar,
    FinancialSummary,
    LocalCsvAdapter,
    StockMaster,
)


def copy_sample_data(tmp_path: Path) -> Path:
    source_dir = Path("data/sample")
    target_dir = tmp_path / "sample"
    target_dir.mkdir()

    for source in source_dir.glob("*.csv"):
        target = target_dir / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    return target_dir


def replace_first_data_value(path: Path, column: str, value: str) -> None:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fieldnames = list(rows[0].keys())

    rows[0][column] = value

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_local_csv_adapter_loads_sample_data():
    adapter = LocalCsvAdapter()

    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summaries = adapter.load_financial_summaries()
    announcement_events = adapter.load_announcement_events()

    assert len(stock_master) >= 10
    assert len({item.stock_code for item in stock_master}) >= 10
    assert len({item.trade_date for item in daily_bars}) >= 60
    assert len({item.stock_code for item in daily_bars}) >= 10
    assert all(isinstance(item, StockMaster) for item in stock_master)
    assert all(isinstance(item, DailyBar) for item in daily_bars)
    assert all(isinstance(item, FinancialSummary) for item in financial_summaries)
    assert all(isinstance(item, AnnouncementEvent) for item in announcement_events)


def test_invalid_date_format_is_rejected(tmp_path):
    data_dir = copy_sample_data(tmp_path)
    replace_first_data_value(data_dir / "daily_bar.csv", "trade_date", "20260102")

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        LocalCsvAdapter(data_dir).load_daily_bars()


def test_negative_price_is_rejected(tmp_path):
    data_dir = copy_sample_data(tmp_path)
    replace_first_data_value(data_dir / "daily_bar.csv", "close", "-1")

    with pytest.raises(ValueError):
        LocalCsvAdapter(data_dir).load_daily_bars()


def test_negative_amount_is_rejected(tmp_path):
    data_dir = copy_sample_data(tmp_path)
    replace_first_data_value(data_dir / "daily_bar.csv", "amount", "-0.01")

    with pytest.raises(ValueError):
        LocalCsvAdapter(data_dir).load_daily_bars()


def test_unknown_stock_code_is_rejected(tmp_path):
    data_dir = copy_sample_data(tmp_path)
    replace_first_data_value(data_dir / "announcement_event.csv", "stock_code", "999999.SZ")

    with pytest.raises(ValueError, match="unknown stock_code"):
        LocalCsvAdapter(data_dir).load_announcement_events()
