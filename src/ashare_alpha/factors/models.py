from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FactorMissingReason(StrEnum):
    NO_BARS = "NO_BARS"
    NO_LATEST_BAR_ON_DATE = "NO_LATEST_BAR_ON_DATE"
    NOT_TRADING_ON_DATE = "NOT_TRADING_ON_DATE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INSUFFICIENT_MOMENTUM_WINDOW = "INSUFFICIENT_MOMENTUM_WINDOW"
    INSUFFICIENT_VOLATILITY_WINDOW = "INSUFFICIENT_VOLATILITY_WINDOW"
    INSUFFICIENT_LIQUIDITY_WINDOW = "INSUFFICIENT_LIQUIDITY_WINDOW"
    INVALID_PRICE_DATA = "INVALID_PRICE_DATA"


MISSING_REASON_TEXT: dict[FactorMissingReason, str] = {
    FactorMissingReason.NO_BARS: "没有任何历史日线数据",
    FactorMissingReason.NO_LATEST_BAR_ON_DATE: "目标交易日没有日线数据",
    FactorMissingReason.NOT_TRADING_ON_DATE: "目标交易日未交易，无法计算当日因子",
    FactorMissingReason.INSUFFICIENT_HISTORY: "历史交易日数量不足，无法计算完整因子",
    FactorMissingReason.INSUFFICIENT_MOMENTUM_WINDOW: "历史交易日数量不足，无法计算动量因子",
    FactorMissingReason.INSUFFICIENT_VOLATILITY_WINDOW: "历史交易日数量不足，无法计算波动因子",
    FactorMissingReason.INSUFFICIENT_LIQUIDITY_WINDOW: "历史交易日数量不足，无法计算流动性因子",
    FactorMissingReason.INVALID_PRICE_DATA: "价格数据异常",
}


class FactorDailyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    ts_code: str = Field(min_length=1)
    latest_close: float | None = Field(default=None, ge=0)
    latest_open: float | None = Field(default=None, ge=0)
    latest_high: float | None = Field(default=None, ge=0)
    latest_low: float | None = Field(default=None, ge=0)
    latest_amount: float | None = Field(default=None, ge=0)
    latest_turnover_rate: float | None = None
    return_1d: float | None = None
    momentum_5d: float | None = None
    momentum_20d: float | None = None
    momentum_60d: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    close_above_ma20: bool | None = None
    close_above_ma60: bool | None = None
    volatility_20d: float | None = Field(default=None, ge=0)
    max_drawdown_20d: float | None = Field(default=None, le=0)
    amount_mean_20d: float | None = Field(default=None, ge=0)
    turnover_mean_20d: float | None = Field(default=None, ge=0)
    limit_up_recent_count: int = Field(ge=0)
    limit_down_recent_count: int = Field(ge=0)
    trading_days_used: int = Field(ge=0)
    is_computable: bool
    missing_reasons: list[str] = Field(default_factory=list)
    missing_reason_text: str = ""

    @model_validator(mode="after")
    def validate_missing_reason_consistency(self) -> FactorDailyRecord:
        if not self.is_computable and not self.missing_reasons:
            raise ValueError("missing_reasons must not be empty when is_computable is false")
        if self.is_computable and self.missing_reasons:
            raise ValueError("missing_reasons must be empty when is_computable is true")
        return self


def missing_reason_text(reason: FactorMissingReason | str) -> str:
    return MISSING_REASON_TEXT[FactorMissingReason(reason)]


def join_missing_reason_text(reasons: list[FactorMissingReason | str]) -> str:
    return "；".join(missing_reason_text(reason) for reason in reasons)
