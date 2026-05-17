from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.gates.models import ResearchGateReport
from ashare_alpha.gates.storage import (
    load_research_gate_report_json,
    save_research_gate_issues_csv,
    save_research_gate_report_json,
    save_research_gate_report_md,
)


def test_gate_storage_round_trip_and_writes_all_formats(tmp_path: Path) -> None:
    report = ResearchGateReport(
        report_id="gate",
        generated_at=datetime.now(),
        gate_config_path="configs/ashare_alpha/gates/research_quality_gates.yaml",
        sources=[],
        overall_decision="PASS",
        pass_count=0,
        warn_count=0,
        block_count=0,
        issue_count=0,
        blocker_count=0,
        warning_count=0,
        info_count=0,
        artifact_summaries=[],
        issues=[],
        summary="pass",
    )

    save_research_gate_report_json(report, tmp_path / "research_gate_report.json")
    save_research_gate_report_md(report, tmp_path / "research_gate_report.md")
    save_research_gate_issues_csv(report, tmp_path / "research_gate_issues.csv")

    loaded = load_research_gate_report_json(tmp_path / "research_gate_report.json")
    assert loaded.report_id == "gate"
    assert (tmp_path / "research_gate_report.md").exists()
    assert (tmp_path / "research_gate_issues.csv").exists()
