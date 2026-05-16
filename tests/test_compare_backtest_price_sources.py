from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_compare_backtest_price_sources_outputs_all_formats(tmp_path: Path) -> None:
    output_dir = tmp_path / "compare"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "compare-backtest-price-sources",
            "--start",
            "2026-01-05",
            "--end",
            "2026-03-20",
            "--left",
            "raw",
            "--right",
            "qfq",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["left"] == "raw"
    assert payload["right"] == "qfq"
    assert payload["execution_price_source"] == "raw"
    assert (output_dir / "left" / "metrics.json").exists()
    assert (output_dir / "right" / "metrics.json").exists()
    assert (output_dir / "backtest_price_source_compare.json").exists()
    assert (output_dir / "backtest_price_source_compare.md").exists()
    assert (output_dir / "backtest_price_source_compare.csv").exists()
