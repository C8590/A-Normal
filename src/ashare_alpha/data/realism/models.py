from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CalendarExchange = Literal["sse", "szse", "bse", "all"]
RealismBoard = Literal["main", "chinext", "star", "bse", "unknown"]
ListingStatus = Literal["listed", "suspended", "delisting_risk", "delisted", "unknown"]
AdjustmentType = Literal["qfq", "hfq", "none", "raw"]
CorporateActionType = Literal["dividend", "bonus_share", "transfer_share", "rights_issue", "split", "other"]


class RealismModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


class TradeCalendarRecord(RealismModel):
    calendar_date: date
    exchange: CalendarExchange
    is_open: bool
    previous_open_date: date | None = None
    next_open_date: date | None = None
    notes: str | None = None

    @field_validator("previous_open_date", "next_open_date", "notes", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @model_validator(mode="after")
    def validate_neighbor_dates(self) -> TradeCalendarRecord:
        if self.previous_open_date is not None and self.previous_open_date >= self.calendar_date:
            raise ValueError("previous_open_date must be earlier than calendar_date")
        if self.next_open_date is not None and self.next_open_date <= self.calendar_date:
            raise ValueError("next_open_date must be later than calendar_date")
        return self


class StockStatusHistoryRecord(RealismModel):
    ts_code: str = Field(min_length=1)
    effective_start: date
    effective_end: date | None = None
    board: RealismBoard | None = None
    industry: str | None = None
    is_st: bool
    is_star_st: bool
    is_suspended: bool
    is_delisting_risk: bool
    listing_status: ListingStatus
    source_name: str | None = None
    available_at: datetime | None = None
    notes: str | None = None

    @field_validator("effective_end", "board", "industry", "source_name", "available_at", "notes", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @model_validator(mode="after")
    def validate_effective_range(self) -> StockStatusHistoryRecord:
        if self.effective_end is not None and self.effective_end < self.effective_start:
            raise ValueError("effective_end must be greater than or equal to effective_start")
        return self


class AdjustmentFactorRecord(RealismModel):
    ts_code: str = Field(min_length=1)
    trade_date: date
    adj_factor: float = Field(gt=0)
    adj_type: AdjustmentType
    source_name: str | None = None
    available_at: datetime | None = None
    notes: str | None = None

    @field_validator("source_name", "available_at", "notes", mode="before")
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)


class CorporateActionRecord(RealismModel):
    ts_code: str = Field(min_length=1)
    action_date: date
    ex_date: date | None = None
    record_date: date | None = None
    publish_date: date | None = None
    action_type: CorporateActionType
    cash_dividend: float | None = Field(default=None, ge=0)
    bonus_share_ratio: float | None = Field(default=None, ge=0)
    transfer_share_ratio: float | None = Field(default=None, ge=0)
    rights_issue_ratio: float | None = Field(default=None, ge=0)
    source_name: str | None = None
    available_at: datetime | None = None
    notes: str | None = None

    @field_validator(
        "ex_date",
        "record_date",
        "publish_date",
        "cash_dividend",
        "bonus_share_ratio",
        "transfer_share_ratio",
        "rights_issue_ratio",
        "source_name",
        "available_at",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_values(cls, value: Any) -> Any:
        return _empty_to_none(value)
