from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


START = "2026-01-05"
END = "2026-03-20"


def test_train_probability_model_default_sample_runs() -> None:
    result = _run(["train-probability-model", "--start", START, "--end", END])

    assert result.returncode == 0
    assert "Probability model trained" in result.stdout


def test_train_probability_model_json_runs() -> None:
    result = _run(["train-probability-model", "--start", START, "--end", END, "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["dataset_rows"] > 0


def test_train_probability_model_requires_start_and_end() -> None:
    result = _run(["train-probability-model", "--start", START])

    assert result.returncode != 0
    assert "--end" in result.stderr


def test_train_probability_model_rejects_start_after_end() -> None:
    result = _run(["train-probability-model", "--start", END, "--end", START])

    assert result.returncode == 1
    assert "start must be earlier" in result.stderr


def test_train_probability_model_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "probability"
    result = _run(["train-probability-model", "--start", START, "--end", END, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "probability_dataset.csv").exists()
    assert (output_dir / "model.json").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "test_predictions.csv").exists()
    assert (output_dir / "summary.md").exists()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
