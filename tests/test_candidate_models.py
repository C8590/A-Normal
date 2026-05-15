from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.candidates import CandidateRecord, CandidateScore, CandidateSelectionReport, CandidateSource


def test_candidate_record_valid() -> None:
    record = CandidateRecord(
        candidate_id="candidate_1",
        name="candidate 1",
        source_type="sweep",
        source_path="outputs/sweeps/sweep_result.json",
        metrics={"total_return": 0.1},
    )

    assert record.candidate_id == "candidate_1"
    assert record.metrics["total_return"] == 0.1


def test_candidate_score_rejects_invalid_recommendation() -> None:
    with pytest.raises(ValidationError):
        CandidateScore(
            candidate_id="candidate_1",
            name="candidate 1",
            total_score=50,
            return_score=50,
            drawdown_score=50,
            stability_score=50,
            trade_activity_score=50,
            warning_penalty_score=0,
            passed_basic_filters=True,
            recommendation="BEST",
        )


def test_candidate_selection_report_serializes() -> None:
    score = CandidateScore(
        candidate_id="candidate_1",
        name="candidate 1",
        total_score=80,
        return_score=90,
        drawdown_score=90,
        stability_score=80,
        trade_activity_score=70,
        warning_penalty_score=0,
        passed_basic_filters=True,
        recommendation="ADVANCE",
    )
    report = CandidateSelectionReport(
        selection_id="selection_1",
        generated_at=datetime(2026, 5, 14, 12, 0, 0),
        rules_path="rules.yaml",
        sources=[CandidateSource(source_type="sweep", path="sweep_result.json", source_id="sweep_1")],
        total_candidates=1,
        advance_count=1,
        review_count=0,
        reject_count=0,
        scores=[score],
        summary="仅用于研究筛选。",
    )

    payload = report.model_dump(mode="json")

    assert payload["selection_id"] == "selection_1"
    assert payload["scores"][0]["recommendation"] == "ADVANCE"
