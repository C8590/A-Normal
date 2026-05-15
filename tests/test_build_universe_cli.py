from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SAMPLE_DATE = "2026-03-20"


def test_build_universe_cli_default_sample_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "build-universe", "--date", SAMPLE_DATE],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Universe built" in result.stdout
    assert "Allowed stocks:" in result.stdout


def test_build_universe_cli_json_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "build-universe", "--date", SAMPLE_DATE, "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 12
    assert payload["excluded"] > 0


def test_build_universe_cli_requires_date() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "build-universe"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--date" in result.stderr


def test_build_universe_cli_writes_custom_output(tmp_path: Path) -> None:
    output_path = tmp_path / "custom_universe.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "build-universe",
            "--date",
            SAMPLE_DATE,
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()


def test_build_universe_cli_missing_data_dir_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "build-universe",
            "--date",
            SAMPLE_DATE,
            "--data-dir",
            str(tmp_path / "missing"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing CSV file" in result.stdout
