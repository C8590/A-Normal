from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


DATE = "2026-03-20"
VALID_CONFIG_DIR = Path("tests/fixtures/configs/valid")


def test_run_pipeline_default_does_not_execute_security_check(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline"
    result = _run(["run-pipeline", "--date", DATE, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "security_check" not in [step["name"] for step in manifest["steps"]]


def test_run_pipeline_check_security_records_step(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline"
    result = _run(["run-pipeline", "--date", DATE, "--check-security", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "security_check" in [step["name"] for step in manifest["steps"]]
    assert (output_dir / "security" / "security_scan_report.json").exists()


def test_run_pipeline_check_security_fails_on_security_error(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    (config_dir / "leaky.yaml").write_text(yaml.safe_dump({"api_key": "plain-secret-value-123"}), encoding="utf-8")
    output_dir = tmp_path / "pipeline"

    result = _run(
        [
            "run-pipeline",
            "--date",
            DATE,
            "--check-security",
            "--config-dir",
            str(config_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result.returncode != 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["steps"][0]["name"] == "security_check"


def test_run_pipeline_check_security_passes_with_default_security(tmp_path: Path) -> None:
    result = _run(["run-pipeline", "--date", DATE, "--check-security", "--output-dir", str(tmp_path / "pipeline")])

    assert result.returncode == 0


def _copy_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(VALID_CONFIG_DIR, config_dir)
    return config_dir


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
