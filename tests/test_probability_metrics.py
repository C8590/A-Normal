from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.probability import evaluate_predictions
from ashare_alpha.probability.models import ProbabilityDatasetRecord, ProbabilityPredictionRecord


def test_accuracy_precision_recall_and_brier_score() -> None:
    metrics = evaluate_predictions(_records([1, 0, 1, 0]), _predictions([0.8, 0.7, 0.4, 0.2]), [5], 0.5)[0]

    assert metrics.accuracy == 0.5
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert round(metrics.brier_score, 4) == round(((0.8 - 1) ** 2 + 0.7**2 + (0.4 - 1) ** 2 + 0.2**2) / 4, 4)


def test_auc_none_with_single_class() -> None:
    metrics = evaluate_predictions(_records([1, 1]), _predictions([0.8, 0.9]), [5], 0.5)[0]

    assert metrics.auc is None


def test_auc_calculates_for_two_classes() -> None:
    metrics = evaluate_predictions(_records([0, 0, 1, 1]), _predictions([0.1, 0.4, 0.35, 0.8]), [5], 0.5)[0]

    assert round(metrics.auc, 2) == 0.75


def test_empty_horizon_metrics_do_not_crash() -> None:
    metrics = evaluate_predictions([], [], [5], 0.5)[0]

    assert metrics.sample_count == 0
    assert metrics.accuracy is None


def _records(labels: list[int]) -> list[ProbabilityDatasetRecord]:
    return [_record(index, label) for index, label in enumerate(labels)]


def _predictions(probabilities: list[float]) -> list[ProbabilityPredictionRecord]:
    return [_prediction(index, probability) for index, probability in enumerate(probabilities)]


def _record(index: int, label: int) -> ProbabilityDatasetRecord:
    return ProbabilityDatasetRecord(
        trade_date=date(2026, 1, 1) + timedelta(days=index),
        ts_code=f"600{index:03d}.SH",
        symbol=f"600{index:03d}",
        name="测试",
        industry="工业",
        stock_score=70,
        raw_score=70,
        risk_penalty_score=0,
        market_regime_score=60,
        industry_strength_score=60,
        trend_momentum_score=60,
        fundamental_quality_score=60,
        liquidity_score=60,
        event_component_score=60,
        volatility_control_score=60,
        event_score=0,
        event_risk_score=0,
        universe_allowed=True,
        signal="WATCH",
        risk_level="low",
        latest_close=10,
        future_return_5d=0.01 if label else -0.01,
        y_win_5d=label,
        is_trainable=True,
        missing_reasons=[],
    )


def _prediction(index: int, probability: float) -> ProbabilityPredictionRecord:
    return ProbabilityPredictionRecord(
        trade_date=date(2026, 1, 1) + timedelta(days=index),
        ts_code=f"600{index:03d}.SH",
        symbol=f"600{index:03d}",
        name="测试",
        industry="工业",
        is_predictable=True,
        missing_reasons=[],
        stock_score=70,
        risk_level="low",
        signal="WATCH",
        latest_close=10,
        p_win_5d=probability,
        expected_return_5d=0.01,
        confidence_level="medium",
        bin_index_5d=0,
        bin_sample_count_5d=10,
        reason="基于 stock_score 分箱校准得到概率",
    )
