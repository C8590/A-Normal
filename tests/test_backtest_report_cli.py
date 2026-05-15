from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


START = "2026-01-05"
END = "2026-03-20"


def test_backtest_report_default_sample_runs() -> None:
    result = _run(["backtest-report", "--start", START, "--end", END])

    assert result.returncode == 0
    assert "Backtest report generated" in result.stdout


def test_backtest_report_json_runs() -> None:
    result = _run(["backtest-report", "--start", START, "--end", END, "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["start_date"] == START


def test_backtest_report_reuse_backtest_dir_runs(tmp_path: Path) -> None:
    backtest_dir = tmp_path / "backtest"
    run_result = _run(["run-backtest", "--start", START, "--end", END, "--output-dir", str(backtest_dir)])
    assert run_result.returncode == 0

    result = _run(
        [
            "backtest-report",
            "--start",
            START,
            "--end",
            END,
            "--reuse-backtest-dir",
            str(backtest_dir),
        ]
    )

    assert result.returncode == 0


def test_backtest_report_requires_start_and_end() -> None:
    result = _run(["backtest-report", "--start", START])

    assert result.returncode != 0
    assert "--end" in result.stderr


def test_backtest_report_rejects_start_after_end() -> None:
    result = _run(["backtest-report", "--start", END, "--end", START])

    assert result.returncode == 1
    assert "start must be earlier" in result.stderr


def test_backtest_report_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "backtest_report"
    result = _run(["backtest-report", "--start", START, "--end", END, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "backtest_report.md").exists()
    assert (output_dir / "backtest_report.json").exists()
    assert (output_dir / "symbol_summary.csv").exists()
    assert (output_dir / "reject_reasons.csv").exists()


def test_existing_cli_commands_still_run() -> None:
    commands = [
        ["validate-data"],
        ["show-config"],
        ["build-universe", "--date", END],
        ["compute-factors", "--date", END],
        ["compute-events", "--date", END],
        ["generate-signals", "--date", END],
        ["run-backtest", "--start", START, "--end", END],
    ]

    for command in commands:
        assert _run(command).returncode == 0


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
