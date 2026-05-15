from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProbabilityModelBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ProbabilityDatasetRecord(ProbabilityModelBase):
    trade_date: date
    ts_code: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    industry: str | None = None

    stock_score: float = Field(ge=0, le=100)
    raw_score: float = Field(ge=0, le=100)
    risk_penalty_score: float = Field(ge=0, le=100)
    market_regime_score: float = Field(ge=0, le=100)
    industry_strength_score: float = Field(ge=0, le=100)
    trend_momentum_score: float = Field(ge=0, le=100)
    fundamental_quality_score: float = Field(ge=0, le=100)
    liquidity_score: float = Field(ge=0, le=100)
    event_component_score: float = Field(ge=0, le=100)
    volatility_control_score: float = Field(ge=0, le=100)
    event_score: float
    event_risk_score: float = Field(ge=0, le=100)
    universe_allowed: bool
    signal: str = Field(min_length=1)
    risk_level: str = Field(min_length=1)
    latest_close: float = Field(gt=0)

    future_return_5d: float | None = None
    future_return_10d: float | None = None
    future_return_20d: float | None = None
    y_win_5d: int | None = None
    y_win_10d: int | None = None
    y_win_20d: int | None = None

    is_trainable: bool
    missing_reasons: list[str] = Field(default_factory=list)

    @field_validator("y_win_5d", "y_win_10d", "y_win_20d")
    @classmethod
    def validate_win_label(cls, value: int | None) -> int | None:
        if value is not None and value not in {0, 1}:
            raise ValueError("win label must be 0 or 1")
        return value

    @model_validator(mode="after")
    def validate_missing_reasons(self) -> ProbabilityDatasetRecord:
        if not self.is_trainable and not self.missing_reasons:
            raise ValueError("missing_reasons must not be empty when is_trainable is false")
        return self


class BinCalibration(ProbabilityModelBase):
    bin_index: int = Field(ge=0)
    lower_bound: float
    upper_bound: float
    sample_count: int = Field(ge=0)
    win_count: int = Field(ge=0)
    raw_win_rate: float = Field(ge=0, le=1)
    smoothed_win_probability: float = Field(ge=0, le=1)
    mean_future_return: float
    smoothed_expected_return: float


class HorizonModel(ProbabilityModelBase):
    horizon: int = Field(gt=0)
    score_field: str = Field(min_length=1)
    global_sample_count: int = Field(ge=0)
    global_win_rate: float = Field(ge=0, le=1)
    global_mean_return: float
    bins: list[BinCalibration] = Field(default_factory=list)
    trained: bool
    reason: str | None = None


class ProbabilityModel(ProbabilityModelBase):
    model_type: str = "score_bin_calibrator"
    trained_at: datetime
    train_start_date: date
    train_end_date: date
    test_start_date: date | None
    test_end_date: date | None
    horizons: list[int]
    score_field: str
    n_bins: int = Field(ge=2)
    prior_strength: float = Field(ge=0)
    horizon_models: dict[str, HorizonModel] = Field(default_factory=dict)
    feature_columns: list[str] = Field(default_factory=list)


class ProbabilityPredictionRecord(ProbabilityModelBase):
    trade_date: date
    ts_code: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    industry: str | None = None
    is_predictable: bool
    missing_reasons: list[str] = Field(default_factory=list)

    stock_score: float | None = Field(default=None, ge=0, le=100)
    risk_level: str | None = None
    signal: str | None = None
    latest_close: float | None = Field(default=None, gt=0)

    p_win_5d: float | None = Field(default=None, ge=0, le=1)
    p_win_10d: float | None = Field(default=None, ge=0, le=1)
    p_win_20d: float | None = Field(default=None, ge=0, le=1)
    expected_return_5d: float | None = None
    expected_return_10d: float | None = None
    expected_return_20d: float | None = None

    confidence_level: str
    bin_index_5d: int | None = None
    bin_index_10d: int | None = None
    bin_index_20d: int | None = None
    bin_sample_count_5d: int | None = None
    bin_sample_count_10d: int | None = None
    bin_sample_count_20d: int | None = None
    reason: str = Field(min_length=1)

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError("confidence_level must be low, medium, or high")
        return value

    @model_validator(mode="after")
    def validate_missing_reasons(self) -> ProbabilityPredictionRecord:
        if not self.is_predictable and not self.missing_reasons:
            raise ValueError("missing_reasons must not be empty when is_predictable is false")
        return self


class ProbabilityMetrics(ProbabilityModelBase):
    horizon: int = Field(gt=0)
    sample_count: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    accuracy: float | None = Field(default=None, ge=0, le=1)
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)
    auc: float | None = Field(default=None, ge=0, le=1)
    brier_score: float | None = Field(default=None, ge=0)
    average_predicted_probability: float | None = Field(default=None, ge=0, le=1)
    actual_win_rate: float | None = Field(default=None, ge=0, le=1)
    average_future_return: float | None = None


class ProbabilityTrainingResult(ProbabilityModelBase):
    model: ProbabilityModel
    metrics: list[ProbabilityMetrics]
    train_rows: int = Field(ge=0)
    test_rows: int = Field(ge=0)
    dataset_rows: int = Field(ge=0)
    skipped_rows: int = Field(ge=0)
    summary: str


FEATURE_COLUMNS = [
    "stock_score",
    "raw_score",
    "risk_penalty_score",
    "market_regime_score",
    "industry_strength_score",
    "trend_momentum_score",
    "fundamental_quality_score",
    "liquidity_score",
    "event_component_score",
    "volatility_control_score",
    "event_score",
    "event_risk_score",
    "universe_allowed",
    "signal",
    "risk_level",
    "latest_close",
]


def get_future_return(record: ProbabilityDatasetRecord, horizon: int) -> float | None:
    return getattr(record, f"future_return_{horizon}d", None)


def get_win_label(record: ProbabilityDatasetRecord, horizon: int) -> int | None:
    return getattr(record, f"y_win_{horizon}d", None)


def set_horizon_value(payload: dict[str, Any], prefix: str, horizon: int, value: Any) -> None:
    key = f"{prefix}_{horizon}d"
    if key in ProbabilityDatasetRecord.model_fields or key in ProbabilityPredictionRecord.model_fields:
        payload[key] = value
