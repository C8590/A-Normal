from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_pipeline_record_experiment_generates_record(tmp_path: Path) -> None:
    registry_dir = tmp_path / "experiments"
    result = _run(
        [
            "run-pipeline",
            "--date",
            "2026-03-20",
            "--output-dir",
            str(tmp_path / "pipeline"),
            "--record-experiment",
            "--experiment-tag",
            "mvp",
            "--experiment-registry-dir",
            str(registry_dir),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["experiment_id"]
    assert (registry_dir / "index.json").exists()
    assert (registry_dir / "records" / f"{payload['experiment_id']}.json").exists()


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
