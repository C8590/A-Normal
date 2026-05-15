from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.universe import UniverseDailyRecord


def test_universe_daily_record_validates_allowed() -> None:
    record = UniverseDailyRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        symbol="600001",
        name="Sample",
        exchange="sse",
        board="main",
        industry="industrial",
        is_allowed=True,
        exclude_reasons=[],
        exclude_reason_text="",
        listing_days=3000,
        latest_close=12.5,
        one_lot_value=1250,
        avg_amount_20d=12000000,
        trading_days_20d=20,
        liquidity_score=60,
        risk_score=0,
        has_recent_negative_event=False,
        recent_negative_event_count=0,
        latest_negative_event_title=None,
    )

    assert record.is_allowed is True


def test_disallowed_record_requires_reason() -> None:
    with pytest.raises(ValidationError, match="exclude_reasons"):
        UniverseDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            symbol="600001",
            name="Sample",
            exchange="sse",
            board="main",
            industry=None,
            is_allowed=False,
            exclude_reasons=[],
            exclude_reason_text="",
            trading_days_20d=20,
            liquidity_score=60,
            risk_score=10,
            has_recent_negative_event=False,
            recent_negative_event_count=0,
        )


def test_liquidity_score_must_be_0_to_100() -> None:
    with pytest.raises(ValidationError):
        UniverseDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            symbol="600001",
            name="Sample",
            exchange="sse",
            board="main",
            industry=None,
            is_allowed=True,
            exclude_reasons=[],
            exclude_reason_text="",
            trading_days_20d=20,
            liquidity_score=101,
            risk_score=10,
            has_recent_negative_event=False,
            recent_negative_event_count=0,
        )


def test_risk_score_must_be_0_to_100() -> None:
    with pytest.raises(ValidationError):
        UniverseDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            symbol="600001",
            name="Sample",
            exchange="sse",
            board="main",
            industry=None,
            is_allowed=True,
            exclude_reasons=[],
            exclude_reason_text="",
            trading_days_20d=20,
            liquidity_score=60,
            risk_score=-1,
            has_recent_negative_event=False,
            recent_negative_event_count=0,
        )
