from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_backtest_report_displays_reused_price_source(tmp_path: Path) -> None:
    backtest_dir = tmp_path / "backtest_qfq"
    report_dir = tmp_path / "report"
    run_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "run-backtest",
            "--start",
            "2026-01-05",
            "--end",
            "2026-03-20",
            "--price-source",
            "qfq",
            "--output-dir",
            str(backtest_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0

    report_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "backtest-report",
            "--start",
            "2026-01-05",
            "--end",
            "2026-03-20",
            "--reuse-backtest-dir",
            str(backtest_dir),
            "--output-dir",
            str(report_dir),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert report_result.returncode == 0
    payload = json.loads(report_result.stdout)
    assert payload["price_source"] == "qfq"
    report_json = json.loads((report_dir / "backtest_report.json").read_text(encoding="utf-8"))
    assert report_json["execution_price_source"] == "raw"
    assert "Adjusted valuation is for research only" in report_json["adjusted_research_note"]
    assert "price_source: qfq" in (report_dir / "backtest_report.md").read_text(encoding="utf-8")
