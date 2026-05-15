from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.data.models import _validate_date_format


class FactorDaily(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str = Field(min_length=1)
    trade_date: date
    close: float | None = Field(default=None, ge=0)
    momentum_5d: float | None = None
    momentum_20d: float | None = None
    momentum_60d: float | None = None
    volatility_20d: float | None = Field(default=None, ge=0)
    max_drawdown_20d: float | None = Field(default=None, le=0)
    amount_mean_20d: float | None = Field(default=None, ge=0)
    turnover_mean_20d: float | None = Field(default=None, ge=0)
    close_above_ma20: bool | None = None
    close_above_ma60: bool | None = None
    limit_up_recent_count: int = Field(default=0, ge=0)
    limit_down_recent_count: int = Field(default=0, ge=0)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)
