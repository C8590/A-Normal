from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.cli import main


def test_evaluate_research_gates_warn_returns_zero(tmp_path: Path) -> None:
    source = tmp_path / "metrics.json"
    source.write_text(json.dumps({"filled_trade_count": 0, "trade_count": 0, "max_drawdown": 0, "sharpe": 0}), encoding="utf-8")
    output_dir = tmp_path / "gates"

    rc = main(["evaluate-research-gates", "--source", str(source), "--output-dir", str(output_dir)])

    assert rc == 0
    assert (output_dir / "research_gate_report.json").exists()
    assert (output_dir / "research_gate_report.md").exists()
    assert (output_dir / "research_gate_issues.csv").exists()


def test_evaluate_research_gates_block_returns_nonzero(tmp_path: Path) -> None:
    source = tmp_path / "security_scan_report.json"
    source.write_text(
        json.dumps({"passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0}),
        encoding="utf-8",
    )

    rc = main(["evaluate-research-gates", "--source", str(source), "--output-dir", str(tmp_path / "gates")])

    assert rc == 1
