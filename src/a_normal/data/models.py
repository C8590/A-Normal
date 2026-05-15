from __future__ import annotations

from datetime import date
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date_format(value: Any) -> Any:
    if isinstance(value, str) and not _DATE_PATTERN.match(value):
        raise ValueError("date must use YYYY-MM-DD format")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StockMaster(StrictModel):
    stock_code: str = Field(min_length=1)
    stock_name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    listed_date: date
    industry: str = ""
    is_st: bool = False

    @field_validator("listed_date", mode="before")
    @classmethod
    def validate_listed_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class DailyBar(StrictModel):
    stock_code: str = Field(min_length=1)
    trade_date: date
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: float = Field(ge=0)
    amount: float = Field(ge=0)
    turnover_rate: float | None = Field(default=None, ge=0)
    is_suspended: bool = False

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Any:
        return _validate_date_format(value)

    @model_validator(mode="after")
    def validate_price_range(self) -> DailyBar:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        return self


class FinancialSummary(StrictModel):
    stock_code: str = Field(min_length=1)
    report_date: date
    revenue: float = Field(ge=0)
    net_profit: float
    total_assets: float = Field(ge=0)
    total_equity: float

    @field_validator("report_date", mode="before")
    @classmethod
    def validate_report_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


class AnnouncementEvent(StrictModel):
    stock_code: str = Field(min_length=1)
    event_date: date
    event_type: str = "unknown"
    category: str = Field(min_length=1)
    title: str = Field(min_length=1)

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_event_date(cls, value: Any) -> Any:
        return _validate_date_format(value)
