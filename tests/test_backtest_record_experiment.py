from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_backtest_record_experiment_generates_record(tmp_path: Path) -> None:
    registry_dir = tmp_path / "experiments"
    result = _run(
        [
            "run-backtest",
            "--start",
            "2026-01-05",
            "--end",
            "2026-03-20",
            "--output-dir",
            str(tmp_path / "backtest"),
            "--record-experiment",
            "--experiment-tag",
            "backtest",
            "--experiment-registry-dir",
            str(registry_dir),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["experiment_id"]
    record = json.loads((registry_dir / "records" / f"{payload['experiment_id']}.json").read_text(encoding="utf-8"))
    assert record["command"] == "run-backtest"
    assert record["tags"] == ["backtest"]


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
