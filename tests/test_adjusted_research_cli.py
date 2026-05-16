from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_adjusted_research_report_cli_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted_research"

    result = _run_cli(["--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert "Adjusted research report generated" in result.stdout
    assert (output_dir / "adjusted_research_report.json").exists()
    assert (output_dir / "adjusted_research_report.md").exists()
    assert (output_dir / "adjusted_research_summary.csv").exists()


def test_adjusted_research_report_cli_json_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted_research_json"

    result = _run_cli(["--output-dir", str(output_dir), "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["factor_comparison_count"] == 2
    assert payload["backtest_comparison_count"] == 2


def test_adjusted_research_report_record_experiment_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted_research_exp"
    registry_dir = tmp_path / "experiments"

    result = _run_cli(["--output-dir", str(output_dir), "--record-experiment", "--experiment-registry-dir", str(registry_dir)])

    assert result.returncode == 0
    assert "Experiment id:" in result.stdout
    assert list((registry_dir / "records").glob("*.json"))


def test_adjusted_research_no_forbidden_imports_or_live_order_code() -> None:
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in ("import requests", "import httpx", "import tushare", "import akshare", "from a_normal"):
        assert forbidden not in source_text
    for forbidden in ("def submit_order", "def place_order", ".submit_order(", ".place_order("):
        assert forbidden not in source_text


def _run_cli(extra_args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "adjusted-research-report",
            "--date",
            "2026-03-20",
            "--start",
            "2026-01-05",
            "--end",
            "2026-03-20",
            *extra_args,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
