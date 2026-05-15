from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_record_experiment_runs(tmp_path: Path) -> None:
    output_dir = _output_with_metrics(tmp_path / "out")
    result = _run(
        [
            "record-experiment",
            "--command",
            "run-backtest",
            "--output-dir",
            str(output_dir),
            "--data-dir",
            "data/sample/ashare_alpha",
            "--registry-dir",
            str(tmp_path / "registry"),
            "--tag",
            "mvp",
        ]
    )

    assert result.returncode == 0
    assert "Experiment id:" in result.stdout


def test_record_experiment_json_runs(tmp_path: Path) -> None:
    output_dir = _output_with_metrics(tmp_path / "out")
    result = _run(
        [
            "record-experiment",
            "--command",
            "run-backtest",
            "--output-dir",
            str(output_dir),
            "--registry-dir",
            str(tmp_path / "registry"),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["metrics_count"] == 2


def test_record_experiment_missing_output_dir_fails(tmp_path: Path) -> None:
    result = _run(
        [
            "record-experiment",
            "--command",
            "run-pipeline",
            "--output-dir",
            str(tmp_path / "missing"),
            "--registry-dir",
            str(tmp_path / "registry"),
        ]
    )

    assert result.returncode != 0


def test_list_show_and_compare_experiments_run(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    first = _record(tmp_path / "first", registry_dir)
    second = _record(tmp_path / "second", registry_dir)

    list_result = _run(["list-experiments", "--registry-dir", str(registry_dir)])
    json_result = _run(["list-experiments", "--registry-dir", str(registry_dir), "--format", "json"])
    show_result = _run(["show-experiment", "--id", first, "--registry-dir", str(registry_dir)])
    compare_result = _run(
        [
            "compare-experiments",
            "--baseline",
            first,
            "--target",
            second,
            "--registry-dir",
            str(registry_dir),
        ]
    )

    assert list_result.returncode == 0
    assert json_result.returncode == 0
    assert show_result.returncode == 0
    assert compare_result.returncode == 0
    assert (registry_dir / "comparisons" / f"compare_{first}_{second}.json").exists()
    assert (registry_dir / "comparisons" / f"compare_{first}_{second}.md").exists()


def _record(output_dir: Path, registry_dir: Path) -> str:
    _output_with_metrics(output_dir)
    result = _run(
        [
            "record-experiment",
            "--command",
            "run-backtest",
            "--output-dir",
            str(output_dir),
            "--registry-dir",
            str(registry_dir),
            "--format",
            "json",
        ]
    )
    assert result.returncode == 0
    return json.loads(result.stdout)["experiment_id"]


def _output_with_metrics(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps({"total_return": 0.1, "sharpe": 1.0}), encoding="utf-8")
    (output_dir / "summary.md").write_text("# summary", encoding="utf-8")
    return output_dir


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
