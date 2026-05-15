from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.data import LocalCsvAdapter


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def copy_sample_data(tmp_path: Path) -> Path:
    data_dir = tmp_path / "sample"
    shutil.copytree(SAMPLE_DATA_DIR, data_dir)
    return data_dir


def rewrite_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), list(reader.fieldnames or [])


def test_local_csv_adapter_reads_sample_data() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)

    assert len(adapter.load_stock_master()) == 12
    assert len(adapter.load_daily_bars()) >= 160 * 12
    assert len(adapter.load_financial_summary()) == 12
    assert len(adapter.load_announcement_events()) >= 7


def test_validate_all_passes_for_sample_data() -> None:
    report = LocalCsvAdapter(SAMPLE_DATA_DIR).validate_all()

    assert report.passed is True
    assert report.errors == []
    assert report.row_counts["stock_master"] == 12
    assert report.row_counts["daily_bar"] >= 160 * 12


def test_validate_all_reports_missing_csv_file(tmp_path) -> None:
    data_dir = copy_sample_data(tmp_path)
    (data_dir / "daily_bar.csv").unlink()

    report = LocalCsvAdapter(data_dir).validate_all()

    assert report.passed is False
    assert any("daily_bar.csv" in error and "Missing CSV file" in error for error in report.errors)


def test_validate_all_reports_missing_required_field(tmp_path) -> None:
    data_dir = copy_sample_data(tmp_path)
    rows, fieldnames = read_csv(data_dir / "stock_master.csv")
    fieldnames.remove("ts_code")
    rows = [{key: value for key, value in row.items() if key != "ts_code"} for row in rows]
    rewrite_csv(data_dir / "stock_master.csv", rows, fieldnames)

    report = LocalCsvAdapter(data_dir).validate_all()

    assert report.passed is False
    assert any("stock_master.csv header field ts_code" in error for error in report.errors)


def test_validate_all_reports_unknown_daily_bar_stock_code(tmp_path) -> None:
    data_dir = copy_sample_data(tmp_path)
    rows, fieldnames = read_csv(data_dir / "daily_bar.csv")
    rows[0]["ts_code"] = "999999.SH"
    rewrite_csv(data_dir / "daily_bar.csv", rows, fieldnames)

    report = LocalCsvAdapter(data_dir).validate_all()

    assert report.passed is False
    assert any("daily_bar.csv field ts_code" in error and "999999.SH" in error for error in report.errors)


def test_validate_all_reports_duplicate_daily_bar_key(tmp_path) -> None:
    data_dir = copy_sample_data(tmp_path)
    rows, fieldnames = read_csv(data_dir / "daily_bar.csv")
    rows.append(rows[0].copy())
    rewrite_csv(data_dir / "daily_bar.csv", rows, fieldnames)

    report = LocalCsvAdapter(data_dir).validate_all()

    assert report.passed is False
    assert any("daily_bar.csv fields ts_code,trade_date" in error for error in report.errors)
