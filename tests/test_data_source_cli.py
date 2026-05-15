from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_list_data_sources_cli_runs() -> None:
    result = _run(["list-data-sources"])

    assert result.returncode == 0
    assert "local_csv" in result.stdout


def test_list_data_sources_cli_json_runs() -> None:
    result = _run(["list-data-sources", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert any(item["name"] == "local_csv" for item in payload)


def test_inspect_data_source_local_csv_runs() -> None:
    result = _run(["inspect-data-source", "--name", "local_csv"])

    assert result.returncode == 0
    assert "Local CSV" in result.stdout


def test_inspect_data_source_missing_fails() -> None:
    result = _run(["inspect-data-source", "--name", "missing"])

    assert result.returncode == 1
    assert "Unknown data source" in result.stderr


def test_existing_commands_still_run_after_data_sources(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    train_result = _run(["train-probability-model", "--start", "2026-01-05", "--end", "2026-03-20", "--output-dir", str(model_dir)])
    assert train_result.returncode == 0
    commands = [
        ["validate-data"],
        ["show-config"],
        ["build-universe", "--date", "2026-03-20"],
        ["compute-factors", "--date", "2026-03-20"],
        ["compute-events", "--date", "2026-03-20"],
        ["generate-signals", "--date", "2026-03-20"],
        ["run-backtest", "--start", "2026-01-05", "--end", "2026-03-20"],
        ["daily-report", "--date", "2026-03-20"],
        ["backtest-report", "--start", "2026-01-05", "--end", "2026-03-20"],
        ["predict-probabilities", "--date", "2026-03-20", "--model-dir", str(model_dir)],
        ["run-pipeline", "--date", "2026-03-20"],
    ]

    for command in commands:
        assert _run(command).returncode == 0


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
