from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ashare_alpha.adjusted_research import (
    AdjustedResearchReport,
    load_adjusted_research_report_json,
    save_adjusted_research_report_json,
    save_adjusted_research_report_md,
    save_adjusted_research_summary_csv,
)


def test_adjusted_research_storage_roundtrip(tmp_path: Path) -> None:
    report = AdjustedResearchReport(
        report_id="adjusted_research_test",
        generated_at=datetime(2026, 5, 16, 12, 0, 0),
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        target_date=date(2026, 3, 20),
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        status="SUCCESS",
        warning_items=["INFO: test"],
        output_dir=str(tmp_path),
        summary="ok",
    )

    save_adjusted_research_report_json(report, tmp_path / "adjusted_research_report.json")
    save_adjusted_research_report_md(report, tmp_path / "adjusted_research_report.md")
    save_adjusted_research_summary_csv(report, tmp_path / "adjusted_research_summary.csv")

    loaded = load_adjusted_research_report_json(tmp_path / "adjusted_research_report.json")

    assert loaded.report_id == report.report_id
    assert "qfq/hfq" in (tmp_path / "adjusted_research_report.md").read_text(encoding="utf-8")
    assert (tmp_path / "adjusted_research_summary.csv").exists()
