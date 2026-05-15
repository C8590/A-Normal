from __future__ import annotations

from datetime import date, datetime

from ashare_alpha.probability import (
    load_probability_model_json,
    save_probability_dataset_csv,
    save_probability_metrics_json,
    save_probability_model_json,
    save_probability_predictions_csv,
    save_probability_summary_md,
)
from ashare_alpha.probability.models import (
    HorizonModel,
    ProbabilityDatasetRecord,
    ProbabilityMetrics,
    ProbabilityModel,
    ProbabilityPredictionRecord,
    ProbabilityTrainingResult,
)


def test_model_json_saves_and_loads(tmp_path) -> None:
    path = tmp_path / "model.json"

    save_probability_model_json(_model(), path)

    assert load_probability_model_json(path).model_type == "score_bin_calibrator"


def test_dataset_predictions_metrics_and_summary_save(tmp_path) -> None:
    save_probability_dataset_csv([_dataset_record()], tmp_path / "dataset.csv")
    save_probability_predictions_csv([_prediction()], tmp_path / "predictions.csv")
    save_probability_metrics_json([_metric()], tmp_path / "metrics.json")
    save_probability_summary_md(
        ProbabilityTrainingResult(
            model=_model(),
            metrics=[_metric()],
            train_rows=1,
            test_rows=1,
            dataset_rows=2,
            skipped_rows=0,
            summary="测试摘要",
        ),
        tmp_path / "summary.md",
    )

    assert (tmp_path / "dataset.csv").exists()
    assert (tmp_path / "predictions.csv").exists()
    assert (tmp_path / "metrics.json").exists()
    assert "概率模型训练摘要" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def _model() -> ProbabilityModel:
    return ProbabilityModel(
        trained_at=datetime(2026, 3, 20, 18, 0),
        train_start_date=date(2026, 1, 5),
        train_end_date=date(2026, 2, 28),
        test_start_date=date(2026, 3, 1),
        test_end_date=date(2026, 3, 20),
        horizons=[5],
        score_field="stock_score",
        n_bins=5,
        prior_strength=10,
        horizon_models={
            "5": HorizonModel(
                horizon=5,
                score_field="stock_score",
                global_sample_count=0,
                global_win_rate=0,
                global_mean_return=0,
                bins=[],
                trained=False,
                reason="样本数量不足",
            )
        },
        feature_columns=["stock_score"],
    )


def _metric() -> ProbabilityMetrics:
    return ProbabilityMetrics(
        horizon=5,
        sample_count=1,
        positive_count=1,
        accuracy=1,
        precision=1,
        recall=1,
        auc=None,
        brier_score=0.04,
        average_predicted_probability=0.8,
        actual_win_rate=1,
        average_future_return=0.01,
    )


def _dataset_record() -> ProbabilityDatasetRecord:
    return ProbabilityDatasetRecord(
        trade_date=date(2026, 3, 20),
        ts_code="600001.SH",
        symbol="600001",
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
        future_return_5d=0.01,
        y_win_5d=1,
        is_trainable=True,
        missing_reasons=[],
    )


def _prediction() -> ProbabilityPredictionRecord:
    return ProbabilityPredictionRecord(
        trade_date=date(2026, 3, 20),
        ts_code="600001.SH",
        symbol="600001",
        name="测试",
        industry="工业",
        is_predictable=True,
        missing_reasons=[],
        stock_score=70,
        risk_level="low",
        signal="WATCH",
        latest_close=10,
        p_win_5d=0.8,
        expected_return_5d=0.01,
        confidence_level="medium",
        bin_index_5d=0,
        bin_sample_count_5d=10,
        reason="基于 stock_score 分箱校准得到概率",
    )
