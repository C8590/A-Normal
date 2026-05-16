from __future__ import annotations

from datetime import date
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ashare_alpha.adjusted import AdjustedDailyBarBuilder
from ashare_alpha.data import DailyBar
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord


FactorPriceSource = Literal["raw", "qfq", "hfq"]


class PriceBarRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    ts_code: str = Field(min_length=1)
    open: float | None = Field(default=None, ge=0)
    high: float | None = Field(default=None, ge=0)
    low: float | None = Field(default=None, ge=0)
    close: float | None = Field(default=None, ge=0)
    pre_close: float | None = Field(default=None, ge=0)
    volume: float = Field(ge=0)
    amount: float = Field(ge=0)
    turnover_rate: float | None = None
    is_trading: bool
    price_source: FactorPriceSource
    adjusted_quality_flags: list[str] = Field(default_factory=list)
    adjusted_quality_reason: str | None = None

    @property
    def adjusted_used(self) -> bool:
        return self.price_source != "raw"

    @property
    def has_complete_price(self) -> bool:
        return all(value is not None for value in (self.open, self.high, self.low, self.close, self.pre_close))


def build_price_bars(
    daily_bars: list[DailyBar],
    adjustment_factors: list[AdjustmentFactorRecord] | None,
    corporate_actions: list[CorporateActionRecord] | None,
    price_source: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[PriceBarRecord]:
    if price_source not in {"raw", "qfq", "hfq"}:
        raise ValueError("price_source must be one of raw, qfq, hfq")
    source = cast(FactorPriceSource, price_source)
    if not daily_bars:
        return []

    effective_start = start_date or min(bar.trade_date for bar in daily_bars)
    effective_end = end_date or max(bar.trade_date for bar in daily_bars)
    scoped_bars = [bar for bar in daily_bars if effective_start <= bar.trade_date <= effective_end]
    if source == "raw":
        return sorted((_raw_price_bar(bar) for bar in scoped_bars), key=lambda item: (item.ts_code, item.trade_date))

    builder = AdjustedDailyBarBuilder(
        daily_bars=scoped_bars,
        adjustment_factors=adjustment_factors or [],
        corporate_actions=corporate_actions or [],
        adj_type=source,
    )
    records, _summary = builder.build_for_range(effective_start, effective_end)
    price_bars = [
        PriceBarRecord(
            trade_date=record.trade_date,
            ts_code=record.ts_code,
            open=record.adj_open,
            high=record.adj_high,
            low=record.adj_low,
            close=record.adj_close,
            pre_close=record.adj_pre_close,
            volume=record.volume,
            amount=record.amount,
            turnover_rate=record.turnover_rate,
            is_trading=True,
            price_source=source,
            adjusted_quality_flags=record.quality_flags,
            adjusted_quality_reason=record.quality_reason,
        )
        for record in records
    ]
    return sorted(price_bars, key=lambda item: (item.ts_code, item.trade_date))


def _raw_price_bar(bar: DailyBar) -> PriceBarRecord:
    return PriceBarRecord(
        trade_date=bar.trade_date,
        ts_code=bar.ts_code,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        pre_close=bar.pre_close,
        volume=bar.volume,
        amount=bar.amount,
        turnover_rate=bar.turnover_rate,
        is_trading=bar.is_trading,
        price_source="raw",
        adjusted_quality_flags=[],
        adjusted_quality_reason=None,
    )
