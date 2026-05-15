from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.quality import DataQualityReporter


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_quality_report_includes_realism_row_counts() -> None:
    report = DataQualityReporter(DATA_DIR, CONFIG_DIR).run()

    assert report.row_counts["trade_calendar"] == 90
    assert report.row_counts["stock_status_history"] >= 12
    assert report.coverage["trade_calendar_min_date"] == "2026-01-01"


def test_quality_report_warns_on_overlapping_status_history(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _append_csv_row(
        data_dir / "stock_status_history.csv",
        {
            "ts_code": "600005.SH",
            "effective_start": "2026-03-05",
            "effective_end": "2026-03-15",
            "board": "main",
            "industry": "energy",
            "is_st": "false",
            "is_star_st": "false",
            "is_suspended": "true",
            "is_delisting_risk": "false",
            "listing_status": "suspended",
            "source_name": "test",
            "available_at": "2026-03-05T18:00:00",
            "notes": "overlap fixture",
        },
    )

    report = DataQualityReporter(data_dir, CONFIG_DIR).run()

    assert any(issue.issue_type == "overlapping_status_interval" for issue in report.issues)


def _copy_sample(target_dir: Path) -> Path:
    shutil.copytree(DATA_DIR, target_dir)
    return target_dir


def _append_csv_row(path: Path, row: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
