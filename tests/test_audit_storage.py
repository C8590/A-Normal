from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.audit import (
    LeakageAuditor,
    build_data_snapshot,
    save_data_snapshot_json,
    save_leakage_audit_report_json,
    save_leakage_audit_report_md,
)
from ashare_alpha.data import LocalCsvAdapter


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_audit_storage_writes_report_and_snapshot(tmp_path: Path) -> None:
    adapter = LocalCsvAdapter(DATA_DIR)
    report = LeakageAuditor(DATA_DIR, CONFIG_DIR).audit_for_date(date(2026, 3, 20))
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

    save_leakage_audit_report_json(report, tmp_path / "audit_report.json")
    save_leakage_audit_report_md(report, tmp_path / "audit_report.md")
    save_data_snapshot_json(snapshot, tmp_path / "data_snapshot.json")

    assert (tmp_path / "audit_report.json").exists()
    markdown = (tmp_path / "audit_report.md").read_text(encoding="utf-8")
    assert "数据可见性规则" in markdown
    assert (tmp_path / "data_snapshot.json").exists()

