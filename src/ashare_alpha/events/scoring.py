from __future__ import annotations

from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent
from ashare_alpha.events.classifier import normalize_event_type
from ashare_alpha.events.models import EventScoreRecord
from ashare_alpha.events.rules import clamp, event_type_text


def score_event(event: AnnouncementEvent, trade_date: date, config: ProjectConfig) -> EventScoreRecord | None:
    scoring_config = config.factors.event_scoring
    event_date = event.event_time.date()
    if event_date > trade_date:
        return None

    event_age_days = (trade_date - event_date).days
    if event_age_days > scoring_config.event_window_days:
        return None

    decay_weight = 0.5 ** (event_age_days / scoring_config.decay_half_life_days)
    source_key = normalize_source(event.source)
    source_weight = scoring_config.source_weights.get(
        source_key,
        scoring_config.source_weights.get("unknown", 0.0),
    )
    normalized_event_type = normalize_event_type(event.event_type, event.title)
    base_score = _score_lookup(scoring_config.base_scores, normalized_event_type)
    direction_multiplier = _direction_multiplier(event.event_direction, scoring_config.direction_weights)
    signed_event_score = base_score * event.event_strength * decay_weight * source_weight * direction_multiplier

    risk_base = _score_lookup(scoring_config.risk_scores, normalized_event_type)
    risk_level_weight = scoring_config.risk_level_weights.get(event.event_risk_level, 1.0)
    risk_score = clamp(risk_base * event.event_strength * decay_weight * risk_level_weight, 0, 100)
    event_block_buy = (
        normalized_event_type in scoring_config.block_buy_event_types
        or (
            event.event_risk_level == "high"
            and normalized_event_type in scoring_config.high_risk_event_types
        )
        or risk_score >= 80
    )

    return EventScoreRecord(
        event_time=event.event_time,
        trade_date=trade_date,
        ts_code=event.ts_code,
        title=event.title,
        source=event.source,
        event_type=event.event_type,
        normalized_event_type=normalized_event_type,
        event_direction=event.event_direction,
        event_strength=event.event_strength,
        event_risk_level=event.event_risk_level,
        event_age_days=event_age_days,
        decay_weight=decay_weight,
        source_weight=source_weight,
        base_score=base_score,
        signed_event_score=signed_event_score,
        risk_score=risk_score,
        event_block_buy=event_block_buy,
        event_reason=_event_reason(normalized_event_type, signed_event_score, risk_score, event_block_buy),
    )


def normalize_source(source: str) -> str:
    text = (source or "").strip().lower()
    if "exchange" in text or "sse" in text or "szse" in text:
        return "exchange"
    if "cninfo" in text or "巨潮" in text:
        return "cninfo"
    if "company" in text or "公司" in text:
        return "company"
    if "media" in text or "媒体" in text:
        return "media"
    return "unknown"


def _score_lookup(scores: dict[str, float], event_type: str) -> float:
    return scores.get(event_type, scores["unknown"])


def _direction_multiplier(event_direction: str, direction_weights: dict[str, float]) -> float:
    if direction_weights.get(event_direction, 1.0) == 0:
        return 0.5
    return 1.0


def _event_reason(event_type: str, signed_score: float, risk_score: float, event_block_buy: bool) -> str:
    label = event_type_text(event_type)
    if event_block_buy:
        return f"{label}：触发禁买，风险分 {risk_score:.1f}"
    if signed_score > 0:
        direction_text = "正向事件分"
    elif signed_score < 0:
        direction_text = "负向事件分"
    else:
        direction_text = "中性事件分"
    return f"{label}：{direction_text} {signed_score:.1f}，风险分 {risk_score:.1f}"
