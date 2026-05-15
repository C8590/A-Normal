from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.events import EventDailyRecord, EventScoreRecord


def test_event_score_record_validates() -> None:
    record = _score_record()

    assert record.ts_code == "600001.SH"
    assert record.event_reason


def test_event_score_record_rejects_bad_decay_weight() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 1"):
        _score_record(decay_weight=1.1)


def test_event_score_record_rejects_bad_source_weight() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 1"):
        _score_record(source_weight=1.1)


def test_event_score_record_rejects_bad_risk_score() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        _score_record(risk_score=101)


def test_event_daily_record_validates() -> None:
    record = _daily_record()

    assert record.event_count == 1
    assert record.event_reason


def test_event_daily_record_requires_block_reasons_when_blocked() -> None:
    with pytest.raises(ValidationError, match="block_buy_reasons"):
        _daily_record(event_block_buy=True, block_buy_reasons=[])


def _score_record(**overrides) -> EventScoreRecord:
    payload = {
        "event_time": datetime(2026, 3, 20, 9, 0),
        "trade_date": date(2026, 3, 20),
        "ts_code": "600001.SH",
        "title": "回购方案公告",
        "source": "exchange",
        "event_type": "buyback",
        "normalized_event_type": "buyback",
        "event_direction": "positive",
        "event_strength": 0.8,
        "event_risk_level": "low",
        "event_age_days": 0,
        "decay_weight": 1.0,
        "source_weight": 1.0,
        "base_score": 30.0,
        "signed_event_score": 24.0,
        "risk_score": 2.0,
        "event_block_buy": False,
        "event_reason": "回购事件：正向事件分 24.0，风险分 2.0",
    }
    payload.update(overrides)
    return EventScoreRecord(**payload)


def _daily_record(**overrides) -> EventDailyRecord:
    payload = {
        "trade_date": date(2026, 3, 20),
        "ts_code": "600001.SH",
        "event_score": 24.0,
        "event_risk_score": 2.0,
        "event_count": 1,
        "positive_event_count": 1,
        "negative_event_count": 0,
        "high_risk_event_count": 0,
        "event_block_buy": False,
        "block_buy_reasons": [],
        "latest_event_title": "回购方案公告",
        "latest_negative_event_title": None,
        "event_reason": "正向事件 1 条，负向事件 0 条，事件分 24.0，风险分 2.0",
    }
    payload.update(overrides)
    return EventDailyRecord(**payload)
