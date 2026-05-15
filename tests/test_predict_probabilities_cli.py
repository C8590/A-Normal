from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


START = "2026-01-05"
END = "2026-03-20"
DATE = "2026-03-20"


def test_predict_probabilities_with_model_dir_runs(tmp_path: Path) -> None:
    model_dir = _train_model(tmp_path)
    result = _run(["predict-probabilities", "--date", DATE, "--model-dir", str(model_dir)])

    assert result.returncode == 0
    assert "Probability predictions generated" in result.stdout


def test_predict_probabilities_json_runs(tmp_path: Path) -> None:
    model_dir = _train_model(tmp_path)
    result = _run(["predict-probabilities", "--date", DATE, "--model-dir", str(model_dir), "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["total_stocks"] == 12


def test_predict_probabilities_missing_model_dir_fails(tmp_path: Path) -> None:
    result = _run(["predict-probabilities", "--date", DATE, "--model-dir", str(tmp_path / "missing")])

    assert result.returncode == 1
    assert "model.json" in result.stderr


def test_predict_probabilities_writes_output(tmp_path: Path) -> None:
    model_dir = _train_model(tmp_path)
    output = tmp_path / "probability_daily.csv"
    result = _run(["predict-probabilities", "--date", DATE, "--model-dir", str(model_dir), "--output", str(output)])

    assert result.returncode == 0
    assert output.exists()


def test_existing_cli_commands_still_run_after_probability() -> None:
    commands = [
        ["validate-data"],
        ["show-config"],
        ["build-universe", "--date", DATE],
        ["compute-factors", "--date", DATE],
        ["compute-events", "--date", DATE],
        ["generate-signals", "--date", DATE],
        ["run-backtest", "--start", START, "--end", END],
        ["daily-report", "--date", DATE],
        ["backtest-report", "--start", START, "--end", END],
    ]

    for command in commands:
        assert _run(command).returncode == 0


def _train_model(tmp_path: Path) -> Path:
    model_dir = tmp_path / "model"
    result = _run(["train-probability-model", "--start", START, "--end", END, "--output-dir", str(model_dir)])
    assert result.returncode == 0
    return model_dir


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
