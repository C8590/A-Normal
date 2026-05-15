from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


DATE = "2026-03-20"


def test_daily_report_default_sample_runs() -> None:
    result = _run(["daily-report", "--date", DATE])

    assert result.returncode == 0
    assert "Daily report generated" in result.stdout


def test_daily_report_json_runs() -> None:
    result = _run(["daily-report", "--date", DATE, "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["report_date"] == DATE


def test_daily_report_requires_date() -> None:
    result = _run(["daily-report"])

    assert result.returncode != 0
    assert "--date" in result.stderr


def test_daily_report_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "daily"
    result = _run(["daily-report", "--date", DATE, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "daily_report.md").exists()
    assert (output_dir / "daily_report.json").exists()
    assert (output_dir / "buy_candidates.csv").exists()
    assert (output_dir / "event_risk_stocks.csv").exists()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
