from __future__ import annotations

from pathlib import Path

from ashare_alpha.audit import build_data_snapshot
from ashare_alpha.data import LocalCsvAdapter


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_sample_data_builds_data_snapshot() -> None:
    adapter = LocalCsvAdapter(DATA_DIR)
    snapshot = build_data_snapshot(
        data_dir=DATA_DIR,
        config_dir=CONFIG_DIR,
        source_name="local_csv",
        data_version="sample",
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    )

    assert snapshot.source_name == "local_csv"
    assert snapshot.row_counts == {
        "stock_master": 12,
        "daily_bar": 2160,
        "financial_summary": 12,
        "announcement_event": 8,
    }
    assert snapshot.min_dates["daily_bar"] is not None
    assert snapshot.max_dates["announcement_event"] is not None

