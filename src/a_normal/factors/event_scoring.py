from __future__ import annotations

from datetime import date
from math import pow
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.config import DEFAULT_CONFIG_DIR, _read_yaml
from a_normal.data import AnnouncementEvent
from a_normal.data.models import _validate_date_format


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

EVENT_TYPES = set(EventType.__args__)


class EventTypeScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float
    risk_score: float = Field(ge=0, le=1)
    block_buy: bool = False


class EventIntensityRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    multiplier: float = Field(gt=0)
    keywords: tuple[str, ...] = ()


class EventBlockBuyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_types: tuple[EventType, ...] = ("investigation",)
    high_risk_event_types: tuple[EventType, ...] = ("regulatory_penalty", "litigation")
    high_risk_keywords: tuple[str, ...] = ()
    min_risk_score: float = Field(default=0.9, ge=0, le=1)


class AnnouncementEventScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    freshness_half_life_days: int = Field(default=30, gt=0)
    stale_after_days: int = Field(default=90, ge=0)
    default_event_type: EventType = "unknown"
    event_type_scores: dict[EventType, EventTypeScore]
    keyword_rules: dict[EventType, tuple[str, ...]] = Field(default_factory=dict)
    intensity_rules: dict[str, EventIntensityRule] = Field(default_factory=dict)
    block_buy: EventBlockBuyConfig = Field(default_factory=EventBlockBuyConfig)


class FactorsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    announcement_events: AnnouncementEventScoringConfig


class EventScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stock_code: str
    event_date: date
    event_type: EventType
    event_score: float
    event_risk_score: float = Field(ge=0, le=1)
    event_block_buy: bool
    event_reason: str

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_event_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


def load_factors_config(config_dir: str | Path | None = None) -> FactorsConfig:
    base_dir = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    return FactorsConfig.model_validate(_read_yaml(base_dir / "factors.yaml"))


def parse_event_type(event: AnnouncementEvent, config: AnnouncementEventScoringConfig | None = None) -> EventType:
    event_config = config or load_factors_config().announcement_events
    normalized_event_type = event.event_type.strip().lower()
    if normalized_event_type in EVENT_TYPES and normalized_event_type != "unknown":
        return normalized_event_type  # type: ignore[return-value]

    title = event.title.lower()
    for event_type, keywords in event_config.keyword_rules.items():
        if any(keyword.lower() in title for keyword in keywords):
            return event_type
    return event_config.default_event_type


def score_announcement_event(
    event: AnnouncementEvent,
    as_of_date: str | date | None = None,
    config: AnnouncementEventScoringConfig | None = None,
) -> EventScoreResult:
    event_config = config or load_factors_config().announcement_events
    target_date = _parse_date(as_of_date) if as_of_date is not None else event.event_date
    event_type = parse_event_type(event, event_config)
    type_score = event_config.event_type_scores[event_type]
    intensity_name, intensity_multiplier = _event_intensity(event.title, event_config)
    freshness = _freshness_multiplier(event.event_date, target_date, event_config)

    event_score = round(type_score.score * intensity_multiplier * freshness, 6)
    event_risk_score = round(min(1.0, type_score.risk_score * intensity_multiplier * freshness), 6)
    block_buy = _event_block_buy(event, event_type, event_risk_score, type_score.block_buy, event_config)
    reason = (
        f"type={event_type};intensity={intensity_name};freshness={freshness:.4f};"
        f"title={event.title}"
    )

    return EventScoreResult(
        stock_code=event.stock_code,
        event_date=event.event_date,
        event_type=event_type,
        event_score=event_score,
        event_risk_score=event_risk_score,
        event_block_buy=block_buy,
        event_reason=reason,
    )


def score_announcement_events(
    events: list[AnnouncementEvent],
    as_of_date: str | date | None = None,
    config: AnnouncementEventScoringConfig | None = None,
) -> list[EventScoreResult]:
    event_config = config or load_factors_config().announcement_events
    results: list[EventScoreResult] = []
    for event in events:
        try:
            results.append(score_announcement_event(event, as_of_date=as_of_date, config=event_config))
        except (KeyError, TypeError, ValueError):
            continue
    return results


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    _validate_date_format(value)
    return date.fromisoformat(value)


def _event_intensity(title: str, config: AnnouncementEventScoringConfig) -> tuple[str, float]:
    normalized_title = title.lower()
    for name in ("high", "medium", "low"):
        rule = config.intensity_rules.get(name)
        if rule and any(keyword.lower() in normalized_title for keyword in rule.keywords):
            return name, rule.multiplier
    return "normal", 1.0


def _freshness_multiplier(event_date: date, as_of_date: date, config: AnnouncementEventScoringConfig) -> float:
    age_days = (as_of_date - event_date).days
    if age_days < 0:
        return 0.0
    if age_days > config.stale_after_days:
        return 0.0
    return pow(0.5, age_days / config.freshness_half_life_days)


def _event_block_buy(
    event: AnnouncementEvent,
    event_type: EventType,
    event_risk_score: float,
    type_blocks_buy: bool,
    config: AnnouncementEventScoringConfig,
) -> bool:
    if type_blocks_buy or event_type in config.block_buy.event_types:
        return True
    normalized_title = event.title.lower()
    has_high_risk_keyword = any(keyword.lower() in normalized_title for keyword in config.block_buy.high_risk_keywords)
    is_high_risk_type = event_type in config.block_buy.high_risk_event_types
    return is_high_risk_type and has_high_risk_keyword and event_risk_score >= config.block_buy.min_risk_score
