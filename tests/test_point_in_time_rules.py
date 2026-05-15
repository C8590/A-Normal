from __future__ import annotations

from datetime import date, datetime

import pytest

from ashare_alpha.audit import (
    infer_available_at_for_announcement_event,
    infer_available_at_for_daily_bar,
    infer_available_at_for_financial_summary,
    is_record_available_for_decision,
    make_decision_time,
)
from ashare_alpha.data import AnnouncementEvent, FinancialSummary
from tests.tests_support import daily_bar


def test_daily_bar_available_at_after_close() -> None:
    assert infer_available_at_for_daily_bar(daily_bar()).isoformat() == "2026-03-20T15:30:00"


def test_financial_summary_available_at_uses_publish_date() -> None:
    item = FinancialSummary(report_date="2025-12-31", publish_date="2026-03-25", ts_code="600001.SH")

    assert infer_available_at_for_financial_summary(item).isoformat() == "2026-03-25T00:00:00"


def test_announcement_event_available_at_uses_event_time() -> None:
    event = AnnouncementEvent(
        event_time="2026-03-20T10:15:00",
        ts_code="600001.SH",
        title="公告",
        source="sample",
        event_type="buyback",
        event_direction="positive",
        event_strength=0.5,
        event_risk_level="low",
    )

    assert infer_available_at_for_announcement_event(event).isoformat() == "2026-03-20T10:15:00"


def test_after_close_decision_can_use_same_day_daily_bar() -> None:
    available_at = infer_available_at_for_daily_bar(daily_bar())
    decision_time = make_decision_time(date(2026, 3, 20), "after_close")

    assert is_record_available_for_decision(available_at, decision_time)


def test_before_open_decision_cannot_use_same_day_daily_bar() -> None:
    available_at = infer_available_at_for_daily_bar(daily_bar())
    decision_time = make_decision_time(date(2026, 3, 20), "before_open")

    assert not is_record_available_for_decision(available_at, decision_time)


def test_available_at_equal_decision_time_is_available() -> None:
    timestamp = datetime(2026, 3, 20, 15, 30)

    assert is_record_available_for_decision(timestamp, timestamp)


def test_make_decision_time_rejects_unknown_timing() -> None:
    with pytest.raises(ValueError, match="timing"):
        make_decision_time(date(2026, 3, 20), "midday")

