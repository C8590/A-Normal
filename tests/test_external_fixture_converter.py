from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.contracts import ExternalFixtureConverter


TUSHARE_FIXTURE = Path("tests/fixtures/external_sources/tushare_like")
AKSHARE_FIXTURE = Path("tests/fixtures/external_sources/akshare_like")
TUSHARE_MAPPING = Path("configs/ashare_alpha/data_sources/tushare_like_mapping.yaml")
AKSHARE_MAPPING = Path("configs/ashare_alpha/data_sources/akshare_like_mapping.yaml")


def test_tushare_like_fixture_converts_to_standard_four_tables(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    result = _convert("tushare_like", TUSHARE_FIXTURE, TUSHARE_MAPPING, output_dir)

    assert result.validation_passed is True
    assert {path.name for path in output_dir.glob("*.csv")} == {
        "stock_master.csv",
        "daily_bar.csv",
        "financial_summary.csv",
        "announcement_event.csv",
    }


def test_akshare_like_fixture_converts_to_standard_four_tables(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    result = _convert("akshare_like", AKSHARE_FIXTURE, AKSHARE_MAPPING, output_dir)

    assert result.validation_passed is True
    assert result.row_counts["stock_master"] == 6


def test_converted_result_passes_local_csv_adapter_validate_all(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    _convert("tushare_like", TUSHARE_FIXTURE, TUSHARE_MAPPING, output_dir)

    assert LocalCsvAdapter(output_dir).validate_all().passed is True


def test_tushare_like_normalizes_dates_exchange_board_ts_code_and_defaults(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    _convert("tushare_like", TUSHARE_FIXTURE, TUSHARE_MAPPING, output_dir)

    stock_rows = _read_rows(output_dir / "stock_master.csv")
    daily_rows = _read_rows(output_dir / "daily_bar.csv")
    announcement_rows = _read_rows(output_dir / "announcement_event.csv")

    assert stock_rows[0]["list_date"] == "2010-01-04"
    assert stock_rows[0]["exchange"] == "sse"
    assert {row["board"] for row in stock_rows} >= {"main", "chinext", "star", "bse"}
    assert stock_rows[0]["ts_code"] == "600101.SH"
    assert stock_rows[0]["is_st"] == "false"
    assert daily_rows[0]["volume"] == "100000"
    assert daily_rows[0]["limit_up"] == ""
    assert announcement_rows[0]["event_direction"] == "neutral"


def test_akshare_like_normalizes_unsuffixed_ts_code(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    _convert("akshare_like", AKSHARE_FIXTURE, AKSHARE_MAPPING, output_dir)

    stock_rows = _read_rows(output_dir / "stock_master.csv")

    assert stock_rows[0]["ts_code"] == "600101.SH"
    assert stock_rows[2]["ts_code"] == "000101.SZ"
    assert stock_rows[-1]["ts_code"] == "920101.BJ"


def test_chinese_normalization_rules_are_supported(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(AKSHARE_FIXTURE, tmp_path / "fixture")
    rows = _read_rows(fixture_dir / "stock_info.csv")
    rows[0]["exchange"] = "上海"
    rows[0]["board"] = "主板A股"
    _write_rows(fixture_dir / "stock_info.csv", rows, list(rows[0].keys()))
    output_dir = tmp_path / "converted"

    _convert("akshare_like", fixture_dir, AKSHARE_MAPPING, output_dir)

    converted = _read_rows(output_dir / "stock_master.csv")
    assert converted[0]["exchange"] == "sse"
    assert converted[0]["board"] == "main"


def test_missing_required_field_makes_conversion_fail(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(TUSHARE_FIXTURE, tmp_path / "fixture")
    rows = _read_rows(fixture_dir / "daily.csv")
    fieldnames = [field for field in rows[0] if field != "ts_code"]
    _write_rows(fixture_dir / "daily.csv", [{key: row[key] for key in fieldnames} for row in rows], fieldnames)

    with pytest.raises(ValueError, match="contract validation failed"):
        _convert("tushare_like", fixture_dir, TUSHARE_MAPPING, tmp_path / "converted")


def test_converted_fixture_can_be_used_by_validate_quality_and_import_cli(tmp_path: Path) -> None:
    output_dir = tmp_path / "converted"
    _convert("tushare_like", TUSHARE_FIXTURE, TUSHARE_MAPPING, output_dir)

    assert _run(["validate-data", "--data-dir", str(output_dir)]).returncode == 0
    assert _run(["quality-report", "--data-dir", str(output_dir), "--output-dir", str(tmp_path / "quality")]).returncode == 0
    result = _run(
        [
            "import-data",
            "--source-name",
            "tushare_like",
            "--source-data-dir",
            str(output_dir),
            "--target-root-dir",
            str(tmp_path / "imports"),
            "--data-version",
            "contract_sample",
            "--overwrite",
        ]
    )
    assert result.returncode == 0


def _convert(source_name: str, fixture_dir: Path, mapping_path: Path, output_dir: Path):
    return ExternalFixtureConverter(source_name, fixture_dir, mapping_path, output_dir).convert()


def _copy_fixture(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
