from __future__ import annotations

from ashare_alpha.candidates import CandidateRecord
from ashare_alpha.candidates.scoring import CandidateScorer

from candidate_helpers import candidate_rules


def test_total_score_calculation() -> None:
    score = CandidateScorer(candidate_rules()).score(
        CandidateRecord(
            candidate_id="c1",
            name="c1",
            source_type="walkforward",
            source_path="wf.json",
            metrics={
                "mean_total_return": 0.2,
                "worst_max_drawdown": 0.0,
                "positive_return_ratio": 1.0,
                "std_total_return": 0.0,
                "success_fold_count": 3,
                "total_trade_count": 1,
            },
        )
    )

    assert score.total_score == 82.0
    assert score.recommendation == "ADVANCE"


def test_larger_drawdown_scores_lower() -> None:
    scorer = CandidateScorer(candidate_rules())
    mild = scorer.score(_candidate({"worst_max_drawdown": -0.02}))
    deep = scorer.score(_candidate({"worst_max_drawdown": -0.18}))

    assert deep.drawdown_score < mild.drawdown_score


def test_low_positive_return_ratio_fails_basic_filter() -> None:
    score = CandidateScorer(candidate_rules()).score(_candidate({"positive_return_ratio": 0.25}))

    assert not score.passed_basic_filters
    assert any("正收益窗口比例" in reason for reason in score.filter_reasons)


def test_many_warnings_increase_penalty() -> None:
    scorer = CandidateScorer(candidate_rules())
    clean = scorer.score(_candidate({}))
    warned = scorer.score(_candidate({}, warnings=["样本窗口过少", "多数窗口未取得正收益", "较大回撤窗口"]))

    assert warned.warning_penalty_score > clean.warning_penalty_score
    assert warned.total_score < clean.total_score


def test_empty_metrics_rejected() -> None:
    score = CandidateScorer(candidate_rules()).score(
        CandidateRecord(candidate_id="empty", name="empty", source_type="sweep", source_path="sweep.json")
    )

    assert score.recommendation == "REJECT"
    assert not score.passed_basic_filters


def test_no_trades_adds_trade_warning_but_scores() -> None:
    score = CandidateScorer(candidate_rules()).score(_candidate({"total_trade_count": 0}))

    assert score.trade_activity_score == 50
    assert score.warning_penalty_score > 0


def _candidate(metrics: dict[str, object], warnings: list[str] | None = None) -> CandidateRecord:
    base = {
        "mean_total_return": 0.1,
        "worst_max_drawdown": -0.05,
        "positive_return_ratio": 0.8,
        "std_total_return": 0.02,
        "success_fold_count": 3,
        "total_trade_count": 3,
    }
    base.update(metrics)
    return CandidateRecord(
        candidate_id="candidate",
        name="candidate",
        source_type="walkforward",
        source_path="wf.json",
        metrics=base,
        warnings=warnings or [],
    )
