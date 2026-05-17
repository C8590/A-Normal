from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.candidates import (
    CandidateRecord,
    CandidateSelectionReport,
    CandidateSource,
    save_candidate_selection_report_json,
)
from ashare_alpha.cli import main
from ashare_alpha.gates.models import ResearchGateReport
from ashare_alpha.gates.storage import save_research_gate_report_json


def test_promote_candidate_config_rejects_block_gate_report(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "scoring.yaml").write_text("thresholds:\n  buy: 80\n", encoding="utf-8")
    selection = _selection(config_dir)
    selection_path = tmp_path / "candidate_selection.json"
    save_candidate_selection_report_json(selection, selection_path)
    gate_path = tmp_path / "research_gate_report.json"
    save_research_gate_report_json(_gate_report("BLOCK"), gate_path)

    rc = main(
        [
            "promote-candidate-config",
            "--selection",
            str(selection_path),
            "--candidate-id",
            "candidate",
            "--promoted-name",
            "candidate",
            "--target-root",
            str(tmp_path / "promoted"),
            "--gate-report",
            str(gate_path),
        ]
    )

    assert rc == 1
    assert not (tmp_path / "promoted" / "candidate").exists()


def _selection(config_dir: Path) -> CandidateSelectionReport:
    candidate = CandidateRecord(
        candidate_id="candidate",
        name="candidate",
        source_type="sweep",
        source_path="sweep_result.json",
        config_dir=str(config_dir),
    )
    return CandidateSelectionReport(
        selection_id="selection",
        generated_at=datetime.now(),
        rules_path="rules.yaml",
        sources=[CandidateSource(source_type="sweep", path="sweep_result.json")],
        total_candidates=1,
        advance_count=1,
        review_count=0,
        reject_count=0,
        scores=[
            {
                "candidate_id": "candidate",
                "name": "candidate",
                "total_score": 80,
                "return_score": 80,
                "drawdown_score": 80,
                "stability_score": 80,
                "trade_activity_score": 80,
                "warning_penalty_score": 80,
                "passed_basic_filters": True,
                "filter_reasons": [],
                "recommendation": "ADVANCE",
            }
        ],
        summary="summary",
        candidates=[candidate],
    )


def _gate_report(decision: str) -> ResearchGateReport:
    issue = {
        "severity": "BLOCKER",
        "gate_name": "default",
        "artifact_type": "security",
        "artifact_path": "security_scan_report.json",
        "issue_type": "security_error",
        "message": "security error",
        "recommendation": "fix",
    }
    return ResearchGateReport.model_validate(
        {
            "report_id": "gate",
            "generated_at": datetime.now().isoformat(),
            "gate_config_path": "configs/ashare_alpha/gates/research_quality_gates.yaml",
            "sources": [],
            "overall_decision": decision,
            "pass_count": 0,
            "warn_count": 0,
            "block_count": 0,
            "issue_count": 1,
            "blocker_count": 1,
            "warning_count": 0,
            "info_count": 0,
            "artifact_summaries": [],
            "issues": [issue],
            "summary": "blocked",
        }
    )
