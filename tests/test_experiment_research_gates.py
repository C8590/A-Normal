from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.experiments import extract_metrics_from_output


def test_experiment_extracts_research_gate_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "gates"
    output_dir.mkdir()
    (output_dir / "research_gate_report.json").write_text(
        json.dumps(
            {
                "overall_decision": "WARN",
                "blocker_count": 0,
                "warning_count": 2,
                "issue_count": 2,
            }
        ),
        encoding="utf-8",
    )

    metrics = extract_metrics_from_output(output_dir, "evaluate-research-gates")
    by_name = {metric.name: metric.value for metric in metrics}

    assert by_name["gate_overall_decision"] == "WARN"
    assert by_name["gate_blocker_count"] == 0
    assert by_name["gate_warning_count"] == 2
    assert by_name["gate_issue_count"] == 2
