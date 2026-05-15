from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventScoreRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    event_time: datetime
    trade_date: date
    ts_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    normalized_event_type: str = Field(min_length=1)
    event_direction: str = Field(min_length=1)
    event_strength: float = Field(ge=0, le=1)
    event_risk_level: str = Field(min_length=1)
    event_age_days: int = Field(ge=0)
    decay_weight: float = Field(ge=0, le=1)
    source_weight: float = Field(ge=0, le=1)
    base_score: float
    signed_event_score: float
    risk_score: float = Field(ge=0, le=100)
    event_block_buy: bool
    event_reason: str = Field(min_length=1)


class EventDailyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    trade_date: date
    ts_code: str = Field(min_length=1)
    event_score: float
    event_risk_score: float = Field(ge=0, le=100)
    event_count: int = Field(ge=0)
    positive_event_count: int = Field(ge=0)
    negative_event_count: int = Field(ge=0)
    high_risk_event_count: int = Field(ge=0)
    event_block_buy: bool
    block_buy_reasons: list[str] = Field(default_factory=list)
    latest_event_title: str | None = None
    latest_negative_event_title: str | None = None
    event_reason: str = Field(min_length=1)

    @field_validator("latest_event_title", "latest_negative_event_title", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_block_buy_reason_consistency(self) -> EventDailyRecord:
        if self.event_block_buy and not self.block_buy_reasons:
            raise ValueError("block_buy_reasons must not be empty when event_block_buy is true")
        return self
