from __future__ import annotations

from pathlib import Path

from ashare_alpha.quality import (
    DataQualityReporter,
    save_quality_issues_csv,
    save_quality_report_json,
    save_quality_report_md,
)


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_quality_storage_writes_files(tmp_path: Path) -> None:
    report = DataQualityReporter(DATA_DIR, CONFIG_DIR).run()

    save_quality_report_json(report, tmp_path / "quality_report.json")
    save_quality_report_md(report, tmp_path / "quality_report.md")
    save_quality_issues_csv(report, tmp_path / "quality_issues.csv")

    assert (tmp_path / "quality_report.json").exists()
    assert (tmp_path / "quality_issues.csv").exists()
    markdown = (tmp_path / "quality_report.md").read_text(encoding="utf-8")
    assert "风险提示" in markdown

