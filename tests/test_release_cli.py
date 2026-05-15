from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_show_version_runs() -> None:
    result = _run(["show-version"])

    assert result.returncode == 0
    assert "0.1.0-mvp" in result.stdout
    assert "package_location" in result.stdout


def test_show_version_json_runs() -> None:
    result = _run(["show-version", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "0.1.0-mvp"


def test_release_check_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"

    result = _run(["release-check", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert "checks_passed" in result.stdout
    assert (output_dir / "release_manifest.json").exists()
    assert (output_dir / "release_checklist.md").exists()


def test_release_check_json_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"

    result = _run(["release-check", "--output-dir", str(output_dir), "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "0.1.0-mvp"
    assert payload["checks_passed"] is True
    assert payload["output_dir"] == str(output_dir)


def test_existing_key_commands_still_run_after_release_cli() -> None:
    for args in (["show-config"], ["validate-data"]):
        result = _run(args)
        assert result.returncode == 0


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
