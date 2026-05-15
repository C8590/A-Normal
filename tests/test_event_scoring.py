from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from ashare_alpha.config import load_project_config
from ashare_alpha.data import AnnouncementEvent
from ashare_alpha.events import score_event


SAMPLE_DATE = date(2026, 3, 20)


def test_future_event_returns_none() -> None:
    event = _event(event_time=datetime.combine(SAMPLE_DATE + timedelta(days=1), datetime.min.time()))

    assert score_event(event, SAMPLE_DATE, load_project_config()) is None


def test_expired_event_returns_none() -> None:
    event = _event(event_time=datetime.combine(SAMPLE_DATE - timedelta(days=21), datetime.min.time()))

    assert score_event(event, SAMPLE_DATE, load_project_config()) is None


def test_same_day_event_has_full_decay_weight() -> None:
    record = score_event(_event(), SAMPLE_DATE, load_project_config())

    assert record is not None
    assert record.event_age_days == 0
    assert record.decay_weight == 1


def test_half_life_decay_is_correct() -> None:
    event = _event(event_time=datetime.combine(SAMPLE_DATE - timedelta(days=7), datetime.min.time()))
    record = score_event(event, SAMPLE_DATE, load_project_config())

    assert record is not None
    assert record.decay_weight == pytest.approx(0.5)


def test_buyback_generates_positive_event_score() -> None:
    record = score_event(_event(event_type="buyback", event_direction="positive"), SAMPLE_DATE, load_project_config())

    assert record is not None
    assert record.signed_event_score > 0
    assert "正向事件分" in record.event_reason


def test_shareholder_reduce_generates_negative_event_score() -> None:
    record = score_event(
        _event(event_type="shareholder_reduce", event_direction="negative", title="股东减持计划"),
        SAMPLE_DATE,
        load_project_config(),
    )

    assert record is not None
    assert record.signed_event_score < 0
    assert "负向事件分" in record.event_reason


def test_investigation_triggers_block_buy() -> None:
    record = score_event(
        _event(event_type="investigation", event_direction="negative", event_risk_level="high", title="立案调查"),
        SAMPLE_DATE,
        load_project_config(),
    )

    assert record is not None
    assert record.event_block_buy is True
    assert "触发禁买" in record.event_reason


def test_high_risk_score_is_clamped_to_100() -> None:
    record = score_event(
        _event(
            event_type="investigation",
            event_direction="negative",
            event_risk_level="high",
            event_strength=1.0,
            title="立案调查",
        ),
        SAMPLE_DATE,
        load_project_config(),
    )

    assert record is not None
    assert record.risk_score == 100


def test_neutral_event_score_is_reduced() -> None:
    config = load_project_config()
    positive = score_event(_event(event_type="equity_pledge", event_direction="negative"), SAMPLE_DATE, config)
    neutral = score_event(_event(event_type="equity_pledge", event_direction="neutral"), SAMPLE_DATE, config)

    assert positive is not None
    assert neutral is not None
    assert abs(neutral.signed_event_score) == pytest.approx(abs(positive.signed_event_score) * 0.5)


def _event(
    event_time: datetime | None = None,
    event_type: str = "buyback",
    event_direction: str = "positive",
    event_strength: float = 1.0,
    event_risk_level: str = "low",
    title: str = "回购方案公告",
    source: str = "exchange",
) -> AnnouncementEvent:
    return AnnouncementEvent(
        event_time=event_time or datetime(2026, 3, 20, 9, 0),
        ts_code="600001.SH",
        title=title,
        source=source,
        event_type=event_type,
        event_direction=event_direction,
        event_strength=event_strength,
        event_risk_level=event_risk_level,
        raw_text=None,
    )
