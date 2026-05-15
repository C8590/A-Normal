from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validate_data_cli_default_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "validate-data"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Data validation passed" in result.stdout
    assert "daily_bar" in result.stdout


def test_validate_data_cli_json_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "validate-data", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["row_counts"]["stock_master"] == 12


def test_validate_data_cli_missing_dir_fails(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "validate-data", "--data-dir", str(missing_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing CSV file" in result.stdout
