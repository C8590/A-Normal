from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.candidates import (
    CandidatePromotionResult,
    CandidateRecord,
    CandidateScore,
    CandidateSelectionReport,
    CandidateSource,
    load_candidate_selection_report_json,
    save_candidate_scores_csv,
    save_candidate_selection_report_json,
    save_candidate_selection_report_md,
    save_promotion_result_json,
)


def test_candidate_selection_json_save_load(tmp_path: Path) -> None:
    report = _report()
    path = tmp_path / "candidate_selection.json"

    save_candidate_selection_report_json(report, path)
    loaded = load_candidate_selection_report_json(path)

    assert loaded.selection_id == report.selection_id
    assert loaded.scores[0].candidate_id == "candidate"


def test_candidate_selection_md_and_csv_save(tmp_path: Path) -> None:
    report = _report()

    save_candidate_selection_report_md(report, tmp_path / "candidate_selection.md")
    save_candidate_scores_csv(report, tmp_path / "candidate_scores.csv")

    assert "候选配置评估报告" in (tmp_path / "candidate_selection.md").read_text(encoding="utf-8")
    assert "candidate" in (tmp_path / "candidate_scores.csv").read_text(encoding="utf-8-sig")


def test_promotion_result_json_save(tmp_path: Path) -> None:
    result = CandidatePromotionResult(
        candidate_id="candidate",
        promoted_name="promoted",
        source_config_dir="config",
        target_config_dir="outputs/promoted",
        copied_files=["scoring.yaml"],
        status="SUCCESS",
        message="ok",
    )

    save_promotion_result_json(result, tmp_path / "promotion_manifest.json")

    assert "candidate" in (tmp_path / "promotion_manifest.json").read_text(encoding="utf-8")


def _report() -> CandidateSelectionReport:
    score = CandidateScore(
        candidate_id="candidate",
        name="candidate",
        total_score=80,
        return_score=90,
        drawdown_score=90,
        stability_score=80,
        trade_activity_score=70,
        warning_penalty_score=0,
        passed_basic_filters=True,
        recommendation="ADVANCE",
    )
    candidate = CandidateRecord(
        candidate_id="candidate",
        name="candidate",
        source_type="sweep",
        source_path="sweep_result.json",
        config_dir="config",
        metrics={"total_return": 0.1},
    )
    return CandidateSelectionReport(
        selection_id="selection",
        generated_at=datetime(2026, 5, 14, 12, 0, 0),
        rules_path="rules.yaml",
        sources=[CandidateSource(source_type="sweep", path="sweep_result.json", source_id="sweep")],
        total_candidates=1,
        advance_count=1,
        review_count=0,
        reject_count=0,
        scores=[score],
        summary="仅用于研究筛选。",
        candidates=[candidate],
    )
