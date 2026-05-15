from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SAMPLE_DATE = "2026-03-20"


def test_generate_signals_cli_default_sample_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "generate-signals", "--date", SAMPLE_DATE],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Signals generated" in result.stdout
    assert "Market regime:" in result.stdout


def test_generate_signals_cli_json_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "generate-signals", "--date", SAMPLE_DATE, "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 12
    assert "market_regime" in payload


def test_generate_signals_cli_requires_date() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "generate-signals"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--date" in result.stderr


def test_generate_signals_cli_writes_custom_output(tmp_path: Path) -> None:
    output_path = tmp_path / "signal_daily.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "generate-signals",
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


def test_generate_signals_cli_missing_data_dir_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "generate-signals",
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


def test_existing_ashare_alpha_cli_commands_still_run() -> None:
    commands = [
        [sys.executable, "-m", "ashare_alpha", "validate-data"],
        [sys.executable, "-m", "ashare_alpha", "show-config"],
        [sys.executable, "-m", "ashare_alpha", "build-universe", "--date", SAMPLE_DATE],
        [sys.executable, "-m", "ashare_alpha", "compute-factors", "--date", SAMPLE_DATE],
        [sys.executable, "-m", "ashare_alpha", "compute-events", "--date", SAMPLE_DATE],
    ]

    for command in commands:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        assert result.returncode == 0
