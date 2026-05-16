from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_compare_factor_price_sources_outputs_csv_json_md(tmp_path: Path) -> None:
    output_dir = tmp_path / "compare"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "compare-factor-price-sources",
            "--date",
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
    assert (output_dir / "factor_price_source_compare.csv").exists()
    assert (output_dir / "factor_price_source_compare.json").exists()
    assert (output_dir / "factor_price_source_compare.md").exists()
    assert "investment advice" in (output_dir / "factor_price_source_compare.md").read_text(encoding="utf-8")
