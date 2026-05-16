from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AdjustedType = Literal["qfq", "hfq", "raw"]


class AdjustedQualityFlag(StrEnum):
    MISSING_ADJ_FACTOR = "MISSING_ADJ_FACTOR"
    INVALID_ADJ_FACTOR = "INVALID_ADJ_FACTOR"
    FALLBACK_ADJ_TYPE = "FALLBACK_ADJ_TYPE"
    MISSING_BASE_FACTOR = "MISSING_BASE_FACTOR"
    INVALID_RAW_PRICE = "INVALID_RAW_PRICE"
    INVALID_ADJUSTED_PRICE = "INVALID_ADJUSTED_PRICE"
    CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE = "CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE"
    FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION = "FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION"
    STALE_FACTOR = "STALE_FACTOR"
    MISSING_FACTOR_AVAILABLE_AT = "MISSING_FACTOR_AVAILABLE_AT"


class AdjustedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdjustedDailyBarRecord(AdjustedModel):
    trade_date: date
    ts_code: str = Field(min_length=1)
    adj_type: AdjustedType
    raw_open: float = Field(ge=0)
    raw_high: float = Field(ge=0)
    raw_low: float = Field(ge=0)
    raw_close: float = Field(ge=0)
    raw_pre_close: float = Field(ge=0)
    volume: float = Field(ge=0)
    amount: float = Field(ge=0)
    turnover_rate: float | None = None
    adj_factor: float | None = None
    base_adj_factor: float | None = None
    adjustment_ratio: float | None = None
    adj_open: float | None = Field(default=None, ge=0)
    adj_high: float | None = Field(default=None, ge=0)
    adj_low: float | None = Field(default=None, ge=0)
    adj_close: float | None = Field(default=None, ge=0)
    adj_pre_close: float | None = Field(default=None, ge=0)
    raw_return_1d: float | None = None
    adj_return_1d: float | None = None
    is_adjusted: bool
    is_valid: bool
    quality_flags: list[str] = Field(default_factory=list)
    quality_reason: str

    @field_validator("adj_factor", "base_adj_factor", "adjustment_ratio")
    @classmethod
    def validate_positive_optional(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("value must be greater than zero when present")
        return value

    @field_validator("quality_flags")
    @classmethod
    def validate_quality_flags(cls, value: list[str]) -> list[str]:
        valid_flags = {flag.value for flag in AdjustedQualityFlag}
        unknown_flags = sorted(set(value) - valid_flags)
        if unknown_flags:
            raise ValueError(f"unknown quality flag: {unknown_flags[0]}")
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> AdjustedDailyBarRecord:
        if not self.is_valid and not self.quality_flags:
            raise ValueError("quality_flags must not be empty when is_valid is false")
        if self.raw_high < self.raw_low:
            raise ValueError("raw_high must be greater than or equal to raw_low")
        if self.raw_low > self.raw_open or self.raw_low > self.raw_close:
            raise ValueError("raw_low must be less than or equal to raw_open and raw_close")
        if self.raw_high < self.raw_open or self.raw_high < self.raw_close:
            raise ValueError("raw_high must be greater than or equal to raw_open and raw_close")
        if self.adj_high is not None and self.adj_low is not None and self.adj_high < self.adj_low:
            raise ValueError("adj_high must be greater than or equal to adj_low")
        return self


class AdjustedBuildSummary(AdjustedModel):
    trade_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    adj_type: AdjustedType
    total_records: int = Field(ge=0)
    adjusted_records: int = Field(ge=0)
    invalid_records: int = Field(ge=0)
    missing_factor_count: int = Field(ge=0)
    stale_factor_count: int = Field(ge=0)
    output_path: str | None = None
    summary: str = Field(min_length=1)
