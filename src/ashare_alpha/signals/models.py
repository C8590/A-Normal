from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SignalValue = Literal["BUY", "WATCH", "BLOCK"]
RiskLevel = Literal["low", "medium", "high"]


class SignalDailyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    trade_date: date
    ts_code: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    board: str = Field(min_length=1)
    industry: str | None
    universe_allowed: bool
    universe_exclude_reasons: list[str] = Field(default_factory=list)
    universe_exclude_reason_text: str | None = None
    market_regime: str = Field(min_length=1)
    market_regime_score: float = Field(ge=0, le=100)
    industry_strength_score: float = Field(ge=0, le=100)
    trend_momentum_score: float = Field(ge=0, le=100)
    fundamental_quality_score: float = Field(ge=0, le=100)
    liquidity_score: float = Field(ge=0, le=100)
    event_component_score: float = Field(ge=0, le=100)
    volatility_control_score: float = Field(ge=0, le=100)
    raw_score: float = Field(ge=0, le=100)
    risk_penalty_score: float = Field(ge=0, le=100)
    stock_score: float = Field(ge=0, le=100)
    event_score: float
    event_risk_score: float = Field(ge=0, le=100)
    event_block_buy: bool
    event_reason: str | None = None
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    signal: SignalValue
    target_weight: float = Field(ge=0, le=1)
    target_shares: int = Field(ge=0)
    estimated_position_value: float = Field(ge=0)
    buy_reasons: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @field_validator("industry", "universe_exclude_reason_text", "event_reason", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_signal_consistency(self) -> SignalDailyRecord:
        if self.signal == "BUY":
            if self.target_weight <= 0:
                raise ValueError("target_weight must be greater than 0 when signal is BUY")
            if self.target_shares <= 0:
                raise ValueError("target_shares must be greater than 0 when signal is BUY")
            if not self.buy_reasons:
                raise ValueError("buy_reasons must not be empty when signal is BUY")
        if self.signal == "BLOCK":
            if self.target_weight != 0:
                raise ValueError("target_weight must be 0 when signal is BLOCK")
            if self.target_shares != 0:
                raise ValueError("target_shares must be 0 when signal is BLOCK")
            if not self.risk_reasons:
                raise ValueError("risk_reasons must not be empty when signal is BLOCK")
        return self
