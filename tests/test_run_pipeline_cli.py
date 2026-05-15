from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


DATE = "2026-03-20"
START = "2026-01-05"
END = "2026-03-20"


def test_run_pipeline_default_sample_runs() -> None:
    result = _run(["run-pipeline", "--date", DATE])

    assert result.returncode == 0
    assert "Pipeline run" in result.stdout


def test_run_pipeline_json_runs() -> None:
    result = _run(["run-pipeline", "--date", DATE, "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "SUCCESS"


def test_run_pipeline_requires_date() -> None:
    result = _run(["run-pipeline"])

    assert result.returncode != 0
    assert "--date" in result.stderr


def test_run_pipeline_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline"
    result = _run(["run-pipeline", "--date", DATE, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "pipeline_summary.md").exists()
    assert (output_dir / "daily_report" / "daily_report.md").exists()


def test_run_pipeline_with_valid_model_dir_runs(tmp_path: Path) -> None:
    model_dir = _train_model(tmp_path)
    result = _run(["run-pipeline", "--date", DATE, "--model-dir", str(model_dir)])

    assert result.returncode == 0
    assert "Probability predictable: 3" in result.stdout


def test_run_pipeline_invalid_model_dir_partial_returns_zero(tmp_path: Path) -> None:
    result = _run(["run-pipeline", "--date", DATE, "--model-dir", str(tmp_path / "missing")])

    assert result.returncode == 0
    assert "PARTIAL" in result.stdout
    assert "部分步骤失败" in result.stdout


def test_run_pipeline_invalid_model_dir_required_returns_nonzero(tmp_path: Path) -> None:
    result = _run(
        [
            "run-pipeline",
            "--date",
            DATE,
            "--model-dir",
            str(tmp_path / "missing"),
            "--require-probability",
        ]
    )

    assert result.returncode != 0


def test_existing_cli_commands_still_run_after_pipeline(tmp_path: Path) -> None:
    model_dir = _train_model(tmp_path)
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
        ["train-probability-model", "--start", START, "--end", END],
        ["predict-probabilities", "--date", DATE, "--model-dir", str(model_dir)],
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
