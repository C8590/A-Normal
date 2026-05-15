from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


DATE = "2026-03-20"
START = "2026-01-05"
END = "2026-03-20"


def test_audit_leakage_date_runs() -> None:
    result = _run(["audit-leakage", "--date", DATE])

    assert result.returncode == 0
    assert "Point-in-Time leakage audit completed" in result.stdout


def test_audit_leakage_json_runs() -> None:
    result = _run(["audit-leakage", "--date", DATE, "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)["error_count"] == 0


def test_audit_leakage_range_runs() -> None:
    result = _run(["audit-leakage", "--start", START, "--end", END])

    assert result.returncode == 0


def test_audit_leakage_requires_date_or_range() -> None:
    result = _run(["audit-leakage"])

    assert result.returncode != 0
    assert "Provide --date" in result.stderr


def test_audit_leakage_rejects_date_and_range_together() -> None:
    result = _run(["audit-leakage", "--date", DATE, "--start", START, "--end", END])

    assert result.returncode != 0
    assert "not both" in result.stderr


def test_audit_leakage_missing_data_dir_fails(tmp_path: Path) -> None:
    result = _run(["audit-leakage", "--date", DATE, "--data-dir", str(tmp_path / "missing")])

    assert result.returncode != 0


def test_audit_leakage_writes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "audit"
    result = _run(["audit-leakage", "--date", DATE, "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert (output_dir / "audit_report.json").exists()
    assert (output_dir / "audit_report.md").exists()
    assert (output_dir / "data_snapshot.json").exists()


def test_audit_leakage_error_count_returns_nonzero(tmp_path: Path) -> None:
    output_dir = tmp_path / "audit"
    result = _run(["audit-leakage", "--date", DATE, "--source-name", "", "--output-dir", str(output_dir)])

    assert result.returncode != 0
    assert (output_dir / "audit_report.json").exists()
    assert json.loads((output_dir / "audit_report.json").read_text(encoding="utf-8"))["error_count"] > 0


def test_existing_commands_still_run_after_audit() -> None:
    for command in [["validate-data"], ["run-pipeline", "--date", DATE]]:
        assert _run(command).returncode == 0


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )

