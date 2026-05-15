from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Board = Literal["main", "chinext", "star", "bse"]
Exchange = Literal["sse", "szse", "bse"]
EventDirection = Literal["positive", "negative", "neutral"]
EventRiskLevel = Literal["low", "medium", "high"]
EventType = Literal[
    "earnings_positive",
    "earnings_negative",
    "buyback",
    "shareholder_increase",
    "shareholder_reduce",
    "regulatory_penalty",
    "investigation",
    "litigation",
    "major_contract",
    "equity_pledge",
    "unlock_shares",
    "unknown",
]


class DataModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


class StockMaster(DataModel):
    ts_code: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exchange: Exchange
    board: Board
    industry: str | None = None
    list_date: date
    delist_date: date | None = None
    is_st: bool
    is_star_st: bool
    is_suspended: bool
    is_delisting_risk: bool

    @field_validator("industry", "delist_date", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)


class DailyBar(DataModel):
    trade_date: date
    ts_code: str = Field(min_length=1)
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    pre_close: float = Field(ge=0)
    volume: float = Field(ge=0)
    amount: float = Field(ge=0)
    turnover_rate: float | None = None
    limit_up: float | None = None
    limit_down: float | None = None
    is_trading: bool

    @field_validator("turnover_rate", "limit_up", "limit_down", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @model_validator(mode="after")
    def validate_price_shape(self) -> DailyBar:
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be greater than or equal to open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be less than or equal to open and close")
        if self.is_trading and self.amount <= 0:
            raise ValueError("amount must be greater than 0 when is_trading is true")
        return self


class FinancialSummary(DataModel):
    report_date: date
    publish_date: date
    ts_code: str = Field(min_length=1)
    revenue_yoy: float | None = None
    profit_yoy: float | None = None
    net_profit_yoy: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_to_asset: float | None = None
    operating_cashflow_to_profit: float | None = None
    goodwill_to_equity: float | None = None

    @field_validator(
        "revenue_yoy",
        "profit_yoy",
        "net_profit_yoy",
        "roe",
        "gross_margin",
        "debt_to_asset",
        "operating_cashflow_to_profit",
        "goodwill_to_equity",
        mode="before",
    )
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @model_validator(mode="after")
    def validate_publish_date(self) -> FinancialSummary:
        if self.publish_date < self.report_date:
            raise ValueError("publish_date must not be earlier than report_date")
        return self


class AnnouncementEvent(DataModel):
    event_time: datetime
    ts_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    event_type: EventType
    event_direction: EventDirection
    event_strength: float = Field(ge=0, le=1)
    event_risk_level: EventRiskLevel
    raw_text: str | None = None

    @field_validator("raw_text", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)
