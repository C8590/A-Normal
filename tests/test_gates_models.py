from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.gates.models import ResearchGateReport


def _report(overall_decision: str, issues: list[dict]) -> dict:
    return {
        "report_id": "gate",
        "generated_at": datetime.now().isoformat(),
        "gate_config_path": "configs/ashare_alpha/gates/research_quality_gates.yaml",
        "sources": [],
        "overall_decision": overall_decision,
        "pass_count": 0,
        "warn_count": 0,
        "block_count": 0,
        "issue_count": len(issues),
        "blocker_count": sum(1 for issue in issues if issue["severity"] == "BLOCKER"),
        "warning_count": sum(1 for issue in issues if issue["severity"] == "WARNING"),
        "info_count": sum(1 for issue in issues if issue["severity"] == "INFO"),
        "artifact_summaries": [],
        "issues": issues,
        "summary": "summary",
    }


def _issue(severity: str) -> dict:
    return {
        "severity": severity,
        "gate_name": "default",
        "artifact_type": "pipeline",
        "artifact_path": "manifest.json",
        "issue_type": "sample",
        "message": "sample",
        "recommendation": "review",
    }


def test_research_gate_report_pass_warn_block_validation() -> None:
    assert ResearchGateReport.model_validate(_report("PASS", [])).overall_decision == "PASS"
    assert ResearchGateReport.model_validate(_report("WARN", [_issue("WARNING")])).overall_decision == "WARN"
    assert ResearchGateReport.model_validate(_report("BLOCK", [_issue("BLOCKER")])).overall_decision == "BLOCK"


def test_research_gate_report_rejects_mismatched_decision() -> None:
    with pytest.raises(ValidationError):
        ResearchGateReport.model_validate(_report("PASS", [_issue("WARNING")]))
