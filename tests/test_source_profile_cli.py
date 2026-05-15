from __future__ import annotations

import json
import os
import subprocess
import sys


def test_list_source_profiles_runs() -> None:
    result = _run(["list-source-profiles"])

    assert result.returncode == 0
    assert "tushare_like_offline" in result.stdout


def test_list_source_profiles_json_runs() -> None:
    result = _run(["list-source-profiles", "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)[0]["mode"] == "offline_replay"


def test_inspect_source_profile_runs() -> None:
    result = _run(
        [
            "inspect-source-profile",
            "--profile",
            "configs/ashare_alpha/source_profiles/tushare_like_offline.yaml",
        ]
    )

    assert result.returncode == 0
    assert "Can run offline: True" in result.stdout


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
