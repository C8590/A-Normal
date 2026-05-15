from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.quality import DataQualityReporter


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_sample_data_generates_quality_report() -> None:
    report = DataQualityReporter(DATA_DIR, CONFIG_DIR).run()

    assert report.passed is True
    assert report.row_counts["stock_master"] == 12


def test_quality_report_coverage_contains_daily_range() -> None:
    report = DataQualityReporter(DATA_DIR, CONFIG_DIR).run()

    assert report.coverage["daily_bar_min_date"] is not None
    assert report.coverage["daily_bar_max_date"] is not None


def test_validate_all_error_still_outputs_report(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _rewrite_first_row(data_dir / "daily_bar.csv", {"high": "9", "low": "10"})

    report = DataQualityReporter(data_dir, CONFIG_DIR).run()

    assert report.passed is False
    assert any(issue.issue_type == "validation_error" for issue in report.issues)
    assert any(issue.issue_type == "high_below_low" for issue in report.issues)


def test_target_date_after_daily_max_generates_warning() -> None:
    report = DataQualityReporter(DATA_DIR, CONFIG_DIR, target_date=__import__("datetime").date(2026, 12, 31)).run()

    assert any(issue.issue_type == "daily_bar_max_before_target_date" for issue in report.issues)


def _copy_sample(target_dir: Path) -> Path:
    shutil.copytree(DATA_DIR, target_dir)
    return target_dir


def _rewrite_first_row(path: Path, updates: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fieldnames = rows[0].keys()
    rows[0].update(updates)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

