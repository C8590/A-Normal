from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


DATA_DIR = Path("data/sample/ashare_alpha")


def test_quality_report_default_sample_runs() -> None:
    result = _run(["quality-report"])

    assert result.returncode == 0
    assert "Data quality report generated" in result.stdout


def test_quality_report_json_runs() -> None:
    result = _run(["quality-report", "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["error_count"] == 0


def test_quality_report_with_data_dir_runs(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    result = _run(["quality-report", "--data-dir", str(data_dir)])

    assert result.returncode == 0


def test_quality_report_output_dir_files_exist(tmp_path: Path) -> None:
    output_dir = tmp_path / "quality"
    result = _run(["quality-report", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "quality_report.json").exists()
    assert (output_dir / "quality_report.md").exists()
    assert (output_dir / "quality_issues.csv").exists()


def test_quality_report_error_fixture_returns_nonzero(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _rewrite_first_row(data_dir / "daily_bar.csv", {"limit_up": "8", "limit_down": "9"})
    result = _run(["quality-report", "--data-dir", str(data_dir)])

    assert result.returncode != 0


def test_existing_validate_and_pipeline_still_run() -> None:
    assert _run(["validate-data"]).returncode == 0
    assert _run(["run-pipeline", "--date", "2026-03-20"]).returncode == 0


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


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )

