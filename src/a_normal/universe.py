from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.config import DEFAULT_CONFIG_DIR, UniverseConfig, _read_yaml
from a_normal.data import AnnouncementEvent, DailyBar, DataAdapter, LocalCsvAdapter, StockMaster
from a_normal.data.models import _validate_date_format


class UniverseDaily(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str
    is_allowed: bool
    exclude_reasons: tuple[str, ...] = Field(default_factory=tuple)
    liquidity_score: float = Field(ge=0)
    risk_score: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class UniverseData:
    stock_master: list[StockMaster]
    daily_bars: list[DailyBar]
    financial_summaries: list[object]
    announcement_events: list[AnnouncementEvent]


class UniverseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_date: date
    rows: tuple[UniverseDaily, ...]

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value):
        return _validate_date_format(value)


def load_universe_config(config_dir: str | Path | None = None) -> UniverseConfig:
    base_dir = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    return UniverseConfig.model_validate(_read_yaml(base_dir / "universe.yaml"))


def build_universe_daily(
    as_of_date: str | date,
    adapter: DataAdapter | None = None,
    config: UniverseConfig | None = None,
) -> UniverseResult:
    target_date = _parse_date(as_of_date)
    data_adapter = adapter or LocalCsvAdapter()
    universe_config = config or load_universe_config()

    data = UniverseData(
        stock_master=data_adapter.load_stock_master(),
        daily_bars=data_adapter.load_daily_bars(),
        financial_summaries=data_adapter.load_financial_summaries(),
        announcement_events=data_adapter.load_announcement_events(),
    )

    bars_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in data.daily_bars:
        if bar.trade_date <= target_date:
            bars_by_code[bar.stock_code].append(bar)
    for bars in bars_by_code.values():
        bars.sort(key=lambda item: item.trade_date)

    events_by_code: dict[str, list[AnnouncementEvent]] = defaultdict(list)
    for event in data.announcement_events:
        if event.event_date <= target_date:
            events_by_code[event.stock_code].append(event)

    rows = tuple(
        _evaluate_stock(stock, target_date, bars_by_code[stock.stock_code], events_by_code[stock.stock_code], universe_config)
        for stock in sorted(data.stock_master, key=lambda item: item.stock_code)
    )
    return UniverseResult(trade_date=target_date, rows=rows)


def _evaluate_stock(
    stock: StockMaster,
    target_date: date,
    bars: list[DailyBar],
    events: list[AnnouncementEvent],
    config: UniverseConfig,
) -> UniverseDaily:
    reasons: list[str] = []
    latest_bar = bars[-1] if bars else None
    latest_bar_on_target = latest_bar if latest_bar and latest_bar.trade_date == target_date else None
    average_amount = _average_recent_amount(bars, config.liquidity_lookback_days)

    if _is_st_stock(stock):
        reasons.append("st_stock")

    if _has_delisting_risk(stock, events, target_date, config):
        reasons.append("delisting_risk")

    if latest_bar_on_target is None or latest_bar_on_target.is_suspended or latest_bar_on_target.volume == 0:
        reasons.append("suspended")

    if len(bars) < config.min_listing_trading_days:
        reasons.append("listing_days_lt_threshold")

    if not _is_mainboard(stock, config):
        reasons.append("not_mainboard")

    if average_amount < config.min_avg_amount_20d:
        reasons.append("low_liquidity")

    if latest_bar_on_target is not None:
        max_entry_budget = config.initial_capital * config.max_position_pct_for_entry
        if latest_bar_on_target.close * config.lot_size > max_entry_budget:
            reasons.append("price_too_high_for_capital")

    if _has_negative_event(events, target_date, config):
        reasons.append("recent_negative_event")

    risk_score = _risk_score(reasons)
    liquidity_score = _liquidity_score(average_amount, config.min_avg_amount_20d)
    return UniverseDaily(
        ts_code=stock.stock_code,
        is_allowed=not reasons,
        exclude_reasons=tuple(reasons),
        liquidity_score=liquidity_score,
        risk_score=risk_score,
    )


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    _validate_date_format(value)
    return date.fromisoformat(value)


def _average_recent_amount(bars: list[DailyBar], lookback_days: int) -> float:
    if not bars:
        return 0.0
    recent = bars[-lookback_days:]
    return sum(item.amount for item in recent) / len(recent)


def _is_mainboard(stock: StockMaster, config: UniverseConfig) -> bool:
    if stock.exchange not in config.allowed_exchanges:
        return False
    prefixes = config.mainboard_prefixes.get(stock.exchange, ())
    raw_code = stock.stock_code.split(".", maxsplit=1)[0]
    return any(raw_code.startswith(prefix) for prefix in prefixes)


def _is_st_stock(stock: StockMaster) -> bool:
    if stock.is_st:
        return True
    normalized_name = stock.stock_name.strip().upper()
    return re.search(r"(^|\s|\*)(ST)(\s|$)", normalized_name) is not None


def _has_delisting_risk(
    stock: StockMaster,
    events: Iterable[AnnouncementEvent],
    target_date: date,
    config: UniverseConfig,
) -> bool:
    stock_name = stock.stock_name.lower()
    if any(keyword.lower() in stock_name for keyword in config.delisting_risk_keywords):
        return True
    return any(
        _is_recent(event.event_date, target_date, config.negative_event_lookback_days)
        and any(keyword.lower() in event.title.lower() for keyword in config.delisting_risk_keywords)
        for event in events
    )


def _has_negative_event(events: Iterable[AnnouncementEvent], target_date: date, config: UniverseConfig) -> bool:
    categories = {item.lower() for item in config.negative_event_categories}
    keywords = tuple(item.lower() for item in config.negative_event_keywords)
    return any(
        _is_recent(event.event_date, target_date, config.negative_event_lookback_days)
        and (event.category.lower() in categories or any(keyword in event.title.lower() for keyword in keywords))
        for event in events
    )


def _is_recent(event_date: date, target_date: date, lookback_days: int) -> bool:
    return 0 <= (target_date - event_date).days <= lookback_days


def _liquidity_score(average_amount: float, threshold: float) -> float:
    if threshold <= 0:
        return 1.0
    return round(min(1.0, average_amount / threshold), 6)


def _risk_score(reasons: list[str]) -> float:
    severe_reasons = {"st_stock", "delisting_risk", "recent_negative_event"}
    if any(reason in severe_reasons for reason in reasons):
        return 0.0
    if reasons:
        return 0.5
    return 1.0
