from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_adjusted_bars_date_runs_and_writes_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted"
    result = _run(["build-adjusted-bars", "--date", "2026-03-20", "--adj-type", "qfq", "--output-dir", str(output_dir), "--format", "json"])

    assert result.returncode != 2
    payload = json.loads(result.stdout)
    assert payload["total_records"] > 0
    assert (output_dir / "adjusted_daily_bar.csv").exists()
    assert (output_dir / "adjusted_summary.json").exists()
    assert (output_dir / "adjusted_validation.json").exists()
    assert (output_dir / "adjusted_report.md").exists()


def test_build_adjusted_bars_range_runs() -> None:
    result = _run(["build-adjusted-bars", "--start", "2026-01-05", "--end", "2026-03-20", "--adj-type", "qfq", "--format", "json"])

    assert result.returncode != 2
    assert json.loads(result.stdout)["total_records"] > 0


def test_build_adjusted_bars_raw_returns_zero(tmp_path: Path) -> None:
    output_dir = tmp_path / "raw"
    result = _run(["build-adjusted-bars", "--start", "2026-01-05", "--end", "2026-03-20", "--adj-type", "raw", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert "Adjusted daily bars generated" in result.stdout


def test_build_adjusted_bars_requires_date_or_range() -> None:
    result = _run(["build-adjusted-bars"])

    assert result.returncode != 0


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
