from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_check_security_runs(tmp_path: Path) -> None:
    result = _run(["check-security", "--output-dir", str(tmp_path / "security")])

    assert result.returncode == 0
    assert "Security scan completed" in result.stdout
    assert (tmp_path / "security" / "security_scan_report.json").exists()


def test_check_security_json_runs(tmp_path: Path) -> None:
    result = _run(["check-security", "--output-dir", str(tmp_path / "security"), "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["passed"] is True


def test_check_secrets_runs() -> None:
    result = _run(["check-secrets"])

    assert result.returncode == 0
    assert "tushare_stub" in result.stdout


def test_check_secrets_json_runs() -> None:
    result = _run(["check-secrets", "--format", "json"])

    assert result.returncode == 0
    assert isinstance(json.loads(result.stdout), list)


def test_show_network_policy_runs() -> None:
    result = _run(["show-network-policy"])

    assert result.returncode == 0
    assert "offline_mode" in result.stdout


def test_show_network_policy_json_runs() -> None:
    result = _run(["show-network-policy", "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["offline_mode"] is True


def test_check_secrets_redacts_set_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASHARE_ALPHA_TUSHARE_TOKEN", "secret-token-value")

    result = _run(["check-secrets", "--format", "json"], env=os.environ.copy())

    assert result.returncode == 0
    assert "secret-token-value" not in result.stdout
    rows = json.loads(result.stdout)
    tushare = next(row for row in rows if row["source_name"] == "tushare_stub")
    assert tushare["is_set"] is True
    assert tushare["redacted_value"] == "sec****lue"


def test_list_data_sources_shows_security_summary() -> None:
    result = _run(["list-data-sources"])

    assert result.returncode == 0
    assert "security_enabled" in result.stdout


def test_inspect_data_source_shows_security_summary() -> None:
    result = _run(["inspect-data-source", "--name", "local_csv"])

    assert result.returncode == 0
    assert "Security:" in result.stdout


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = env or os.environ.copy()
    command_env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
        env=command_env,
    )
