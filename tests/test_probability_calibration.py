from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.config import load_project_config
from ashare_alpha.probability import ScoreBinCalibrator
from ashare_alpha.probability.models import ProbabilityDatasetRecord


def test_horizon_model_trained_when_samples_sufficient() -> None:
    model = ScoreBinCalibrator(_config(min_train_samples=5, min_bin_samples=3)).fit(_records(20))

    assert model.horizon_models["5"].trained is True


def test_horizon_model_untrained_when_samples_insufficient() -> None:
    model = ScoreBinCalibrator(_config(min_train_samples=50)).fit(_records(5))

    assert model.horizon_models["5"].trained is False
    assert "样本数量不足" in model.horizon_models["5"].reason


def test_bin_count_not_more_than_configured_bins() -> None:
    config = _config(min_train_samples=5, n_bins=4)
    model = ScoreBinCalibrator(config).fit(_records(20))

    assert len(model.horizon_models["5"].bins) <= config.probability.n_bins


def test_smoothed_probability_between_zero_and_one() -> None:
    model = ScoreBinCalibrator(_config(min_train_samples=5)).fit(_records(20))

    assert all(0 <= item.smoothed_win_probability <= 1 for item in model.horizon_models["5"].bins)


def test_predict_one_outputs_all_default_horizons() -> None:
    config = _config(min_train_samples=5)
    calibrator = ScoreBinCalibrator(config)
    model = calibrator.fit(_records(30))
    prediction = calibrator.predict_one(_records(1)[0], model)

    assert prediction.p_win_5d is not None
    assert prediction.p_win_10d is not None
    assert prediction.p_win_20d is not None


def test_low_bin_sample_count_sets_low_confidence() -> None:
    config = _config(min_train_samples=5, min_bin_samples=100)
    calibrator = ScoreBinCalibrator(config)
    prediction = calibrator.predict_one(_records(1)[0], calibrator.fit(_records(20)))

    assert prediction.confidence_level == "low"


def test_missing_score_is_not_predictable() -> None:
    config = _config(min_train_samples=5)
    calibrator = ScoreBinCalibrator(config)
    model = calibrator.fit(_records(20)).model_copy(update={"score_field": "missing_score"})
    prediction = calibrator.predict_one(_records(1)[0], model)

    assert prediction.is_predictable is False


def _config(**updates):
    config = load_project_config()
    probability = config.probability.model_copy(update=updates)
    return config.model_copy(update={"probability": probability})


def _records(count: int) -> list[ProbabilityDatasetRecord]:
    return [_record(index) for index in range(count)]


def _record(index: int) -> ProbabilityDatasetRecord:
    score = 50 + index % 50
    future_return = 0.02 if index % 3 else -0.01
    return ProbabilityDatasetRecord(
        trade_date=date(2026, 1, 1) + timedelta(days=index),
        ts_code=f"600{index:03d}.SH",
        symbol=f"600{index:03d}",
        name="测试",
        industry="工业",
        stock_score=score,
        raw_score=score,
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
        future_return_5d=future_return,
        future_return_10d=future_return,
        future_return_20d=future_return,
        y_win_5d=1 if future_return > 0 else 0,
        y_win_10d=1 if future_return > 0 else 0,
        y_win_20d=1 if future_return > 0 else 0,
        is_trainable=True,
        missing_reasons=[],
    )
