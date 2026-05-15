from __future__ import annotations

import csv
import shutil
from datetime import date
from pathlib import Path

from ashare_alpha.audit import LeakageAuditor


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_audit_leakage_warns_on_future_status_available_at(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _rewrite_status_available_at(data_dir / "stock_status_history.csv", "600005.SH", "2026-03-10", "2026-03-21T18:00:00")

    report = LeakageAuditor(data_dir, CONFIG_DIR).audit_for_date(date(2026, 3, 20))

    assert any(issue.issue_type == "stock_status_not_yet_available" for issue in report.issues)


def test_audit_leakage_warns_on_missing_factor_available_at(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _rewrite_first_row(data_dir / "adjustment_factor.csv", {"available_at": ""})

    report = LeakageAuditor(data_dir, CONFIG_DIR).audit_for_date(date(2026, 3, 20))

    assert any(issue.issue_type == "adjustment_factor_missing_available_at" for issue in report.issues)


def _copy_sample(target_dir: Path) -> Path:
    shutil.copytree(DATA_DIR, target_dir)
    return target_dir


def _rewrite_status_available_at(path: Path, ts_code: str, effective_start: str, available_at: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    for row in rows:
        if row["ts_code"] == ts_code and row["effective_start"] == effective_start:
            row["available_at"] = available_at
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _rewrite_first_row(path: Path, updates: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    rows[0].update(updates)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
