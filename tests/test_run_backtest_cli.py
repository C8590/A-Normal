from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


START = "2026-01-05"
END = "2026-03-20"


def test_run_backtest_cli_default_sample_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "run-backtest", "--start", START, "--end", END],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Backtest run" in result.stdout


def test_run_backtest_cli_json_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "run-backtest", "--start", START, "--end", END, "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["initial_cash"] == 10000


def test_run_backtest_cli_requires_start_and_end() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "run-backtest", "--start", START],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--end" in result.stderr


def test_run_backtest_cli_rejects_start_after_end() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "run-backtest", "--start", END, "--end", START],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "start must be earlier" in result.stderr


def test_run_backtest_cli_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "backtest"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "run-backtest",
            "--start",
            START,
            "--end",
            END,
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (output_dir / "trades.csv").exists()
    assert (output_dir / "daily_equity.csv").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "summary.md").exists()


def test_run_backtest_cli_missing_data_dir_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "run-backtest",
            "--start",
            START,
            "--end",
            END,
            "--data-dir",
            str(tmp_path / "missing"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing CSV file" in result.stdout


def test_existing_cli_commands_still_run() -> None:
    commands = [
        [sys.executable, "-m", "ashare_alpha", "validate-data"],
        [sys.executable, "-m", "ashare_alpha", "show-config"],
        [sys.executable, "-m", "ashare_alpha", "build-universe", "--date", "2026-03-20"],
        [sys.executable, "-m", "ashare_alpha", "compute-factors", "--date", "2026-03-20"],
        [sys.executable, "-m", "ashare_alpha", "compute-events", "--date", "2026-03-20"],
        [sys.executable, "-m", "ashare_alpha", "generate-signals", "--date", "2026-03-20"],
    ]

    for command in commands:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        assert result.returncode == 0
