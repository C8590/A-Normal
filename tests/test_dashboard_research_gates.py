from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.dashboard import DashboardScanner, build_dashboard_summary
from ashare_alpha.gates.models import ResearchGateReport
from ashare_alpha.gates.storage import save_research_gate_report_json


def test_dashboard_scans_research_gate_artifact(tmp_path: Path) -> None:
    gate_dir = tmp_path / "outputs" / "gates" / "gates_1"
    save_research_gate_report_json(_gate_report(), gate_dir / "research_gate_report.json")

    index = DashboardScanner(tmp_path / "outputs").scan()
    summary = build_dashboard_summary(index)

    assert index.artifacts_by_type["research_gate"] == 1
    assert summary.latest_research_gate is not None
    assert summary.latest_research_gate.status == "WARN"
    assert any(item["artifact_type"] == "research_gate" for item in summary.warning_items)


def _gate_report() -> ResearchGateReport:
    issue = {
        "severity": "WARNING",
        "gate_name": "default",
        "artifact_type": "backtest",
        "artifact_path": "metrics.json",
        "issue_type": "backtest_low_trade_count",
        "message": "low trades",
        "recommendation": "review",
    }
    return ResearchGateReport.model_validate(
        {
            "report_id": "gate",
            "generated_at": datetime.now().isoformat(),
            "gate_config_path": "configs/ashare_alpha/gates/research_quality_gates.yaml",
            "sources": [],
            "overall_decision": "WARN",
            "pass_count": 0,
            "warn_count": 0,
            "block_count": 0,
            "issue_count": 1,
            "blocker_count": 0,
            "warning_count": 1,
            "info_count": 0,
            "artifact_summaries": [],
            "issues": [issue],
            "summary": "warn",
        }
    )
