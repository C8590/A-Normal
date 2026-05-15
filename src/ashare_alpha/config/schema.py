from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ashare_alpha.security.models import SecurityConfig


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UniverseConfig(StrictConfigModel):
    allowed_boards: tuple[str, ...]
    excluded_boards: tuple[str, ...]
    exclude_st: bool
    exclude_star_st: bool
    exclude_delisting_risk: bool
    exclude_suspended: bool
    min_listing_days: int = Field(ge=0)
    min_avg_amount_20d: float = Field(ge=0)
    initial_cash_for_affordability: float = Field(gt=0)
    max_one_lot_position_pct: float = Field(gt=0, le=1)
    block_recent_negative_events: bool
    recent_event_window_days: int = Field(ge=0)


class TradingRulesConfig(StrictConfigModel):
    lot_size: int = Field(gt=0)
    price_tick: float = Field(gt=0)
    t_plus_one: bool
    normal_limit_pct: float = Field(gt=0, le=1)
    st_limit_pct: float = Field(gt=0, le=1)
    block_buy_at_limit_up: bool
    block_sell_at_limit_down: bool
    allow_short_selling: bool
    allow_margin_trading: bool


class FeesConfig(StrictConfigModel):
    commission_rate: float = Field(ge=0)
    min_commission: float = Field(ge=0)
    stamp_tax_rate_on_sell: float = Field(ge=0)
    transfer_fee_rate: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)


class FactorsConfig(StrictConfigModel):
    momentum_windows: tuple[int, ...]
    volatility_window: int = Field(gt=0)
    max_drawdown_window: int = Field(gt=0)
    liquidity_window: int = Field(gt=0)
    recent_limit_window: int = Field(gt=0)
    ma_windows: tuple[int, ...]
    event_scoring: EventScoringConfig

    @model_validator(mode="after")
    def require_positive_windows(self) -> FactorsConfig:
        if any(window <= 0 for window in self.momentum_windows):
            raise ValueError("momentum_windows must contain positive integers")
        if any(window <= 0 for window in self.ma_windows):
            raise ValueError("ma_windows must contain positive integers")
        return self


class EventScoringConfig(StrictConfigModel):
    event_window_days: int = Field(ge=0)
    decay_half_life_days: float = Field(gt=0)
    base_scores: dict[str, float]
    risk_scores: dict[str, float]
    block_buy_event_types: tuple[str, ...]
    high_risk_event_types: tuple[str, ...]
    source_weights: dict[str, float]
    direction_weights: dict[str, float]
    risk_level_weights: dict[str, float]

    @model_validator(mode="after")
    def validate_event_scoring_maps(self) -> EventScoringConfig:
        if "unknown" not in self.base_scores:
            raise ValueError("event_scoring.base_scores must include unknown")
        if "unknown" not in self.risk_scores:
            raise ValueError("event_scoring.risk_scores must include unknown")
        for name, weight in self.source_weights.items():
            if not 0 <= weight <= 1:
                raise ValueError(f"source weight must be between 0 and 1: {name}")
        for name, score in self.risk_scores.items():
            if not 0 <= score <= 100:
                raise ValueError(f"risk score must be between 0 and 100: {name}")
        for name, weight in self.risk_level_weights.items():
            if weight < 0:
                raise ValueError(f"risk level weight must be non-negative: {name}")
        return self


class ScoringThresholdsConfig(StrictConfigModel):
    buy: float
    watch: float
    block_risk_level: Literal["low", "medium", "high"]

    @model_validator(mode="after")
    def require_buy_above_watch(self) -> ScoringThresholdsConfig:
        if self.buy <= self.watch:
            raise ValueError("buy threshold must be greater than watch threshold")
        return self


class RiskLevelThresholdsConfig(StrictConfigModel):
    low: float = Field(ge=0, le=100)
    medium: float = Field(ge=0, le=100)
    high: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def require_ordered_thresholds(self) -> RiskLevelThresholdsConfig:
        if not self.low < self.medium < self.high:
            raise ValueError("risk level thresholds must satisfy low < medium < high")
        return self


class PositionSizingConfig(StrictConfigModel):
    min_buy_score: float = Field(ge=0, le=100)
    strong_buy_score: float = Field(ge=0, le=100)
    base_buy_weight: float = Field(gt=0, le=1)
    strong_buy_weight: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def require_ordered_position_sizing(self) -> PositionSizingConfig:
        if self.min_buy_score > self.strong_buy_score:
            raise ValueError("min_buy_score must be less than or equal to strong_buy_score")
        if self.base_buy_weight > self.strong_buy_weight:
            raise ValueError("base_buy_weight must be less than or equal to strong_buy_weight")
        return self


class ScoringConfig(StrictConfigModel):
    weights: dict[str, float]
    thresholds: ScoringThresholdsConfig
    risk_penalty: dict[str, float]
    risk_level_thresholds: RiskLevelThresholdsConfig
    position_sizing: PositionSizingConfig

    @model_validator(mode="after")
    def require_weights_sum_to_one(self) -> ScoringConfig:
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError("scoring weights must sum to 1.0 within 1e-6")
        return self


class BacktestConfig(StrictConfigModel):
    initial_cash: float = Field(gt=0)
    max_positions: int = Field(ge=1)
    max_position_weight: float = Field(gt=0, le=1)
    min_position_value: float = Field(ge=0)
    rebalance_frequency: Literal["daily", "weekly", "monthly"]
    start_date: date | None
    end_date: date | None
    benchmark: str | None
    save_trades: bool
    save_daily_equity: bool
    execution: BacktestExecutionConfig
    metrics: BacktestMetricsConfig


class BacktestExecutionConfig(StrictConfigModel):
    signal_timing: Literal["after_close"]
    execution_price: Literal["next_open"]
    slippage_bps: float | None = Field(default=None, ge=0)
    sell_when_signal_not_buy: bool
    exit_on_block: bool
    allow_partial_fills: bool


class BacktestMetricsConfig(StrictConfigModel):
    annualization_days: int = Field(gt=0)


class ProbabilityOutputConfig(StrictConfigModel):
    save_dataset: bool
    save_test_predictions: bool
    save_model: bool
    save_metrics: bool


class ProbabilityConfig(StrictConfigModel):
    horizons: tuple[int, ...]
    win_return_threshold: float = 0.0
    train_test_split_ratio: float = Field(gt=0, lt=1)
    purge_gap: bool
    n_bins: int = Field(ge=2)
    min_train_samples: int = Field(ge=1)
    min_bin_samples: int = Field(ge=1)
    prior_strength: float = Field(ge=0)
    prediction_threshold: float = Field(ge=0, le=1)
    include_only_universe_allowed: bool
    include_only_computable_factors: bool
    score_field: Literal["stock_score"]
    output: ProbabilityOutputConfig

    @model_validator(mode="after")
    def validate_horizons(self) -> ProbabilityConfig:
        if not self.horizons:
            raise ValueError("probability.horizons must not be empty")
        if any(horizon <= 0 for horizon in self.horizons):
            raise ValueError("probability.horizons must contain positive integers")
        return self


class ProjectConfig(StrictConfigModel):
    universe: UniverseConfig
    trading_rules: TradingRulesConfig
    fees: FeesConfig
    factors: FactorsConfig
    scoring: ScoringConfig
    backtest: BacktestConfig
    probability: ProbabilityConfig
    security: SecurityConfig
