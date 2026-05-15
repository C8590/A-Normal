from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.data.models import _validate_date_format


Side = Literal["BUY", "SELL"]


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)

    ts_code: str
    shares: int = Field(ge=0)
    average_cost: float = Field(ge=0)
    last_buy_date: date | None = None


class TradeLog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    ts_code: str
    side: Side
    price: float = Field(ge=0)
    shares: int = Field(gt=0)
    gross_amount: float = Field(ge=0)
    commission: float = Field(ge=0)
    stamp_tax: float = Field(ge=0)
    total_cost: float = Field(ge=0)
    cash_after: float
    reason: str

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class DailyNav(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    cash: float
    market_value: float = Field(ge=0)
    total_equity: float = Field(ge=0)
    nav: float = Field(ge=0)
    positions: dict[str, int] = Field(default_factory=dict)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    initial_cash: float = Field(gt=0)
    final_equity: float = Field(ge=0)
    daily_nav: tuple[DailyNav, ...]
    trades: tuple[TradeLog, ...]
    metrics: dict[str, float]
