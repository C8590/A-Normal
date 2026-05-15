from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.data.realism import (
    AdjustmentFactorRecord,
    CorporateActionRecord,
    StockStatusHistoryRecord,
    TradeCalendarRecord,
)


def test_realism_models_validate_valid_records() -> None:
    assert TradeCalendarRecord(
        calendar_date="2026-01-02",
        exchange="all",
        is_open=True,
        previous_open_date="2025-12-31",
        next_open_date="2026-01-05",
    ).is_open
    assert StockStatusHistoryRecord(
        ts_code="600001.SH",
        effective_start="2026-01-01",
        board="main",
        is_st=False,
        is_star_st=False,
        is_suspended=False,
        is_delisting_risk=False,
        listing_status="listed",
    ).listing_status == "listed"
    assert AdjustmentFactorRecord(ts_code="600001.SH", trade_date="2026-01-02", adj_factor=1.0, adj_type="qfq")
    assert CorporateActionRecord(ts_code="600001.SH", action_date="2026-02-20", action_type="dividend")


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (TradeCalendarRecord, {"calendar_date": "2026-01-02", "exchange": "hkex", "is_open": True}),
        (
            StockStatusHistoryRecord,
            {
                "ts_code": "600001.SH",
                "effective_start": "2026-01-01",
                "board": "invalid",
                "is_st": False,
                "is_star_st": False,
                "is_suspended": False,
                "is_delisting_risk": False,
                "listing_status": "listed",
            },
        ),
        (AdjustmentFactorRecord, {"ts_code": "600001.SH", "trade_date": "2026-01-02", "adj_factor": 1, "adj_type": "bad"}),
        (CorporateActionRecord, {"ts_code": "600001.SH", "action_date": "2026-02-20", "action_type": "bad"}),
    ],
)
def test_realism_models_reject_invalid_enums(model, payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model(**payload)


def test_realism_models_reject_invalid_ranges() -> None:
    with pytest.raises(ValidationError):
        TradeCalendarRecord(calendar_date="2026-01-02", exchange="all", is_open=True, previous_open_date="2026-01-03")
    with pytest.raises(ValidationError):
        AdjustmentFactorRecord(ts_code="600001.SH", trade_date="2026-01-02", adj_factor=0, adj_type="qfq")
    with pytest.raises(ValidationError):
        CorporateActionRecord(ts_code="600001.SH", action_date="2026-02-20", action_type="dividend", cash_dividend=-1)
