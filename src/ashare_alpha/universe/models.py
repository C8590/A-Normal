from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UniverseDailyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    ts_code: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    board: str = Field(min_length=1)
    industry: str | None
    is_allowed: bool
    exclude_reasons: list[str] = Field(default_factory=list)
    exclude_reason_text: str = ""
    listing_days: int | None = None
    latest_close: float | None = None
    one_lot_value: float | None = Field(default=None, ge=0)
    avg_amount_20d: float | None = Field(default=None, ge=0)
    trading_days_20d: int = Field(ge=0)
    liquidity_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    has_recent_negative_event: bool
    recent_negative_event_count: int = Field(ge=0)
    latest_negative_event_title: str | None = None

    @field_validator("industry", "latest_negative_event_title", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_reason_consistency(self) -> UniverseDailyRecord:
        if not self.is_allowed and not self.exclude_reasons:
            raise ValueError("exclude_reasons must not be empty when is_allowed is false")
        if self.is_allowed and self.exclude_reasons:
            raise ValueError("exclude_reasons must be empty when is_allowed is true")
        return self
