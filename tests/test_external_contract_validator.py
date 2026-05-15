from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.data.contracts import ExternalContractValidator


TUSHARE_FIXTURE = Path("tests/fixtures/external_sources/tushare_like")
AKSHARE_FIXTURE = Path("tests/fixtures/external_sources/akshare_like")


def test_tushare_like_fixture_passes_contract_check() -> None:
    report = ExternalContractValidator("tushare_like", TUSHARE_FIXTURE).validate()

    assert report.passed is True
    assert report.error_count == 0
    assert report.row_counts["daily"] >= 40


def test_akshare_like_fixture_passes_contract_check() -> None:
    report = ExternalContractValidator("akshare_like", AKSHARE_FIXTURE).validate()

    assert report.passed is True
    assert report.error_count == 0
    assert report.row_counts["stock_zh_a_hist"] >= 40


def test_missing_required_field_produces_error(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(TUSHARE_FIXTURE, tmp_path / "fixture")
    _drop_field(fixture_dir / "daily.csv", "ts_code")

    report = ExternalContractValidator("tushare_like", fixture_dir).validate()

    assert report.passed is False
    assert any(issue.issue_type == "missing_required_field" and issue.field_name == "ts_code" for issue in report.issues)


def test_missing_optional_field_produces_info(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(TUSHARE_FIXTURE, tmp_path / "fixture")
    _drop_field(fixture_dir / "daily.csv", "pct_chg")

    report = ExternalContractValidator("tushare_like", fixture_dir).validate()

    assert report.error_count == 0
    assert any(issue.severity == "info" and issue.field_name == "pct_chg" for issue in report.issues)


def test_missing_fixture_dir_produces_error(tmp_path: Path) -> None:
    report = ExternalContractValidator("tushare_like", tmp_path / "missing").validate()

    assert report.passed is False
    assert any(issue.issue_type == "missing_fixture_dir" for issue in report.issues)


def test_empty_csv_produces_warning(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(TUSHARE_FIXTURE, tmp_path / "fixture")
    with (fixture_dir / "daily.csv").open("r", encoding="utf-8-sig", newline="") as stream:
        fieldnames = list(csv.DictReader(stream).fieldnames or [])
    with (fixture_dir / "daily.csv").open("w", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=fieldnames).writeheader()

    report = ExternalContractValidator("tushare_like", fixture_dir).validate()

    assert report.passed is True
    assert any(issue.severity == "warning" and issue.issue_type == "empty_csv" for issue in report.issues)


def _copy_fixture(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _drop_field(path: Path, field_name: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fieldnames = [field for field in reader.fieldnames or [] if field != field_name]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fieldnames})
