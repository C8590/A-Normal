from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SAMPLE_DATE = "2026-03-20"


def test_compute_factors_price_source_raw_runs(tmp_path: Path) -> None:
    output = tmp_path / "factor_raw.csv"

    result = _run(["compute-factors", "--date", SAMPLE_DATE, "--price-source", "raw", "--output", str(output)])

    assert result.returncode == 0
    assert output.exists()
    assert "Price source: raw" in result.stdout


def test_compute_factors_price_source_qfq_runs(tmp_path: Path) -> None:
    output = tmp_path / "factor_qfq.csv"

    result = _run(["compute-factors", "--date", SAMPLE_DATE, "--price-source", "qfq", "--output", str(output)])

    assert result.returncode == 0
    assert output.exists()
    assert "price_source" in output.read_text(encoding="utf-8")
    assert "qfq" in output.read_text(encoding="utf-8")


def test_compute_factors_price_source_hfq_runs_json(tmp_path: Path) -> None:
    output = tmp_path / "factor_hfq.csv"

    result = _run(
        ["compute-factors", "--date", SAMPLE_DATE, "--price-source", "hfq", "--output", str(output), "--format", "json"]
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["price_source"] == "hfq"
    assert output.exists()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
