from __future__ import annotations

import json
import os
import subprocess
import sys


def test_list_data_sources_json_includes_security_fields() -> None:
    result = _run(["list-data-sources", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    local = next(item for item in payload if item["name"] == "local_csv")
    assert local["security_enabled"] is True
    assert local["security_requires_api_key"] is False


def test_inspect_data_source_json_includes_secret_status() -> None:
    result = _run(["inspect-data-source", "--name", "local_csv", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["security"]["secret_is_set"] is False


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
