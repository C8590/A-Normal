from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import exp, log
from statistics import fmean, pstdev
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.data import DailyBar
from a_normal.data.models import _validate_date_format
from a_normal.factors import FactorDaily, build_factor_daily


FEATURE_NAMES = (
    "momentum_5d",
    "momentum_20d",
    "momentum_60d",
    "volatility_20d",
    "max_drawdown_20d",
    "amount_mean_20d",
    "turnover_mean_20d",
    "close_above_ma20",
    "close_above_ma60",
    "limit_up_recent_count",
    "limit_down_recent_count",
)


class LabeledSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str
    trade_date: date
    features: dict[str, float]
    future_5d_return: float
    future_10d_return: float
    future_20d_return: float
    y_5d_win: int = Field(ge=0, le=1)
    y_10d_win: int = Field(ge=0, le=1)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class EvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accuracy: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    auc: float = Field(ge=0, le=1)
    calibration: dict[str, float]


class ProbabilityPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str
    trade_date: date
    p_5d_win: float = Field(ge=0, le=1)
    p_10d_win: float = Field(ge=0, le=1)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class ProbabilityModelResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    message: str
    sample_count: int
    train_count: int
    test_count: int
    evaluation: dict[str, EvaluationMetrics] = Field(default_factory=dict)
    predictions: tuple[ProbabilityPrediction, ...] = Field(default_factory=tuple)


class _FittedBinaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    weights: tuple[float, ...] = ()
    bias: float = 0.0
    constant_probability: float | None = None
    means: tuple[float, ...] = ()
    scales: tuple[float, ...] = ()


def build_labeled_samples(
    daily_bars: list[DailyBar],
    factor_daily: list[FactorDaily] | None = None,
) -> list[LabeledSample]:
    factors = factor_daily or build_factor_daily(daily_bars)
    factor_by_key = {(item.ts_code, item.trade_date): item for item in factors}
    bars_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in daily_bars:
        bars_by_code[bar.stock_code].append(bar)

    samples: list[LabeledSample] = []
    for ts_code, bars in bars_by_code.items():
        sorted_bars = sorted(bars, key=lambda item: item.trade_date)
        for index, bar in enumerate(sorted_bars):
            if index + 20 >= len(sorted_bars) or bar.close <= 0:
                continue
            factor = factor_by_key.get((ts_code, bar.trade_date))
            if factor is None:
                continue
            future_5d_return = _future_return(bar.close, sorted_bars[index + 5].close)
            future_10d_return = _future_return(bar.close, sorted_bars[index + 10].close)
            future_20d_return = _future_return(bar.close, sorted_bars[index + 20].close)
            samples.append(
                LabeledSample(
                    ts_code=ts_code,
                    trade_date=bar.trade_date,
                    features=_features(factor),
                    future_5d_return=future_5d_return,
                    future_10d_return=future_10d_return,
                    future_20d_return=future_20d_return,
                    y_5d_win=1 if future_5d_return > 0 else 0,
                    y_10d_win=1 if future_10d_return > 0 else 0,
                )
            )
    return sorted(samples, key=lambda item: (item.trade_date, item.ts_code))


def train_probability_model(
    daily_bars: list[DailyBar],
    factor_daily: list[FactorDaily] | None = None,
    min_samples: int = 30,
    test_size: float = 0.3,
    epochs: int = 250,
    learning_rate: float = 0.08,
) -> ProbabilityModelResult:
    samples = build_labeled_samples(daily_bars, factor_daily)
    if len(samples) < min_samples:
        return ProbabilityModelResult(
            status="insufficient_samples",
            message=f"样本不足：需要至少 {min_samples} 条，当前 {len(samples)} 条。",
            sample_count=len(samples),
            train_count=0,
            test_count=0,
        )

    train_samples, test_samples = _time_split(samples, test_size)
    if not train_samples or not test_samples:
        return ProbabilityModelResult(
            status="insufficient_samples",
            message="样本不足：按时间切分后训练集或测试集为空。",
            sample_count=len(samples),
            train_count=len(train_samples),
            test_count=len(test_samples),
        )

    train_x = [_feature_vector(item) for item in train_samples]
    test_x = [_feature_vector(item) for item in test_samples]
    y5_train = [item.y_5d_win for item in train_samples]
    y10_train = [item.y_10d_win for item in train_samples]
    y5_test = [item.y_5d_win for item in test_samples]
    y10_test = [item.y_10d_win for item in test_samples]

    model_5d = _fit_binary_model(train_x, y5_train, epochs=epochs, learning_rate=learning_rate)
    model_10d = _fit_binary_model(train_x, y10_train, epochs=epochs, learning_rate=learning_rate)
    p5 = [_predict_probability(model_5d, row) for row in test_x]
    p10 = [_predict_probability(model_10d, row) for row in test_x]

    return ProbabilityModelResult(
        status="ok",
        message="模型训练、预测、评估完成。",
        sample_count=len(samples),
        train_count=len(train_samples),
        test_count=len(test_samples),
        evaluation={
            "p_5d_win": _evaluate(y5_test, p5),
            "p_10d_win": _evaluate(y10_test, p10),
        },
        predictions=tuple(
            ProbabilityPrediction(
                ts_code=sample.ts_code,
                trade_date=sample.trade_date,
                p_5d_win=round(p5[index], 6),
                p_10d_win=round(p10[index], 6),
            )
            for index, sample in enumerate(test_samples)
        ),
    )


def _time_split(samples: list[LabeledSample], test_size: float) -> tuple[list[LabeledSample], list[LabeledSample]]:
    dates = sorted({item.trade_date for item in samples})
    if len(dates) < 2:
        return samples, []
    split_index = max(1, min(len(dates) - 1, int(len(dates) * (1 - test_size))))
    train_dates = set(dates[:split_index])
    return [item for item in samples if item.trade_date in train_dates], [item for item in samples if item.trade_date not in train_dates]


def _fit_binary_model(
    x_rows: list[list[float]],
    y: list[int],
    epochs: int,
    learning_rate: float,
) -> _FittedBinaryModel:
    prior = sum(y) / len(y)
    if len(set(y)) < 2:
        return _FittedBinaryModel(kind="constant", constant_probability=prior)

    means, scales = _fit_scaler(x_rows)
    scaled_x = [_scale(row, means, scales) for row in x_rows]
    weights = [0.0 for _ in FEATURE_NAMES]
    bias = _logit(_clamp(prior, 1e-4, 1 - 1e-4))
    for _epoch in range(epochs):
        grad_w = [0.0 for _ in weights]
        grad_b = 0.0
        for row, target in zip(scaled_x, y):
            pred = _sigmoid(sum(weight * value for weight, value in zip(weights, row)) + bias)
            error = pred - target
            for index, value in enumerate(row):
                grad_w[index] += error * value
            grad_b += error
        n = len(y)
        for index in range(len(weights)):
            weights[index] -= learning_rate * grad_w[index] / n
        bias -= learning_rate * grad_b / n

    return _FittedBinaryModel(
        kind="logistic",
        weights=tuple(weights),
        bias=bias,
        means=tuple(means),
        scales=tuple(scales),
    )


def _predict_probability(model: _FittedBinaryModel, x_row: list[float]) -> float:
    if model.kind == "constant":
        return float(model.constant_probability or 0.0)
    scaled = _scale(x_row, list(model.means), list(model.scales))
    return _sigmoid(sum(weight * value for weight, value in zip(model.weights, scaled)) + model.bias)


def _evaluate(y_true: list[int], probabilities: list[float]) -> EvaluationMetrics:
    predictions = [1 if probability >= 0.5 else 0 for probability in probabilities]
    tp = sum(1 for y, pred in zip(y_true, predictions) if y == 1 and pred == 1)
    tn = sum(1 for y, pred in zip(y_true, predictions) if y == 0 and pred == 0)
    fp = sum(1 for y, pred in zip(y_true, predictions) if y == 0 and pred == 1)
    fn = sum(1 for y, pred in zip(y_true, predictions) if y == 1 and pred == 0)
    accuracy = (tp + tn) / len(y_true) if y_true else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return EvaluationMetrics(
        accuracy=round(accuracy, 6),
        precision=round(precision, 6),
        recall=round(recall, 6),
        auc=round(_auc(y_true, probabilities), 6),
        calibration=_calibration(y_true, probabilities),
    )


def _auc(y_true: list[int], probabilities: list[float]) -> float:
    positives = [score for label, score in zip(y_true, probabilities) if label == 1]
    negatives = [score for label, score in zip(y_true, probabilities) if label == 0]
    if not positives or not negatives:
        return 0.5
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _calibration(y_true: list[int], probabilities: list[float]) -> dict[str, float]:
    bins = [(0.0, 0.33), (0.33, 0.66), (0.66, 1.01)]
    result: dict[str, float] = {
        "mean_predicted_probability": round(fmean(probabilities), 6) if probabilities else 0.0,
        "mean_observed_rate": round(fmean(y_true), 6) if y_true else 0.0,
    }
    for low, high in bins:
        selected = [(label, prob) for label, prob in zip(y_true, probabilities) if low <= prob < high]
        name = f"bin_{low:.2f}_{min(high, 1.0):.2f}"
        result[f"{name}_count"] = float(len(selected))
        result[f"{name}_observed_rate"] = round(fmean([label for label, _prob in selected]), 6) if selected else 0.0
    return result


def _features(factor: FactorDaily) -> dict[str, float]:
    return {
        "momentum_5d": _num(factor.momentum_5d),
        "momentum_20d": _num(factor.momentum_20d),
        "momentum_60d": _num(factor.momentum_60d),
        "volatility_20d": _num(factor.volatility_20d),
        "max_drawdown_20d": _num(factor.max_drawdown_20d),
        "amount_mean_20d": _num(factor.amount_mean_20d),
        "turnover_mean_20d": _num(factor.turnover_mean_20d),
        "close_above_ma20": _bool_num(factor.close_above_ma20),
        "close_above_ma60": _bool_num(factor.close_above_ma60),
        "limit_up_recent_count": float(factor.limit_up_recent_count),
        "limit_down_recent_count": float(factor.limit_down_recent_count),
    }


def _feature_vector(sample: LabeledSample) -> list[float]:
    return [sample.features.get(name, 0.0) for name in FEATURE_NAMES]


def _fit_scaler(x_rows: list[list[float]]) -> tuple[list[float], list[float]]:
    columns = list(zip(*x_rows))
    means = [fmean(column) for column in columns]
    scales = [pstdev(column) or 1.0 for column in columns]
    return means, scales


def _scale(row: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(value - mean) / scale for value, mean, scale in zip(row, means, scales)]


def _future_return(current_close: float, future_close: float) -> float:
    return round(future_close / current_close - 1.0, 10)


def _num(value: float | int | None) -> float:
    return float(value) if value is not None else 0.0


def _bool_num(value: bool | None) -> float:
    if value is None:
        return 0.0
    return 1.0 if value else -1.0


def _sigmoid(value: float) -> float:
    if value >= 35:
        return 1.0
    if value <= -35:
        return 0.0
    return 1 / (1 + exp(-value))


def _logit(probability: float) -> float:
    return log(probability / (1 - probability))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
