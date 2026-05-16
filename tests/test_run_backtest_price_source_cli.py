from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


START = "2026-01-05"
END = "2026-03-20"


def test_run_backtest_price_source_raw_writes_price_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "raw"

    result = _run(["run-backtest", "--start", START, "--end", END, "--price-source", "raw", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["price_source"] == "raw"


def test_run_backtest_price_source_qfq_writes_execution_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "qfq"

    result = _run(["run-backtest", "--start", START, "--end", END, "--price-source", "qfq", "--output-dir", str(output_dir)])

    assert result.returncode == 0
    assert "Price source: qfq" in result.stdout
    header = (output_dir / "trades.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "execution_price_source" in header
    assert "price_source=qfq" in (output_dir / "summary.md").read_text(encoding="utf-8")


def test_run_backtest_price_source_hfq_runs_json(tmp_path: Path) -> None:
    output_dir = tmp_path / "hfq"

    result = _run(
        [
            "run-backtest",
            "--start",
            START,
            "--end",
            END,
            "--price-source",
            "hfq",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["price_source"] == "hfq"
    rows = list(csv.DictReader((output_dir / "daily_equity.csv").open("r", encoding="utf-8")))
    assert rows[0]["price_source"] == "hfq"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "ashare_alpha", *args], check=False, capture_output=True, text=True)
