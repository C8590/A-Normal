from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster


def test_stock_master_validates() -> None:
    stock = StockMaster(
        ts_code="600001.SH",
        symbol="600001",
        name="Sample Main",
        exchange="sse",
        board="main",
        industry="industrial",
        list_date="2010-01-04",
        delist_date="",
        is_st=False,
        is_star_st=False,
        is_suspended=False,
        is_delisting_risk=False,
    )

    assert stock.ts_code == "600001.SH"
    assert stock.delist_date is None


def test_stock_master_rejects_invalid_board() -> None:
    with pytest.raises(ValidationError):
        StockMaster(
            ts_code="600001.SH",
            symbol="600001",
            name="Sample Main",
            exchange="sse",
            board="otc",
            industry=None,
            list_date="2010-01-04",
            delist_date=None,
            is_st=False,
            is_star_st=False,
            is_suspended=False,
            is_delisting_risk=False,
        )


def test_daily_bar_validates() -> None:
    bar = DailyBar(
        trade_date="2026-03-26",
        ts_code="600001.SH",
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        pre_close=10.0,
        volume=10000,
        amount=102000,
        turnover_rate="",
        limit_up=11.0,
        limit_down=9.0,
        is_trading=True,
    )

    assert bar.turnover_rate is None


def test_daily_bar_rejects_high_below_low() -> None:
    with pytest.raises(ValidationError, match="high must be greater"):
        DailyBar(
            trade_date="2026-03-26",
            ts_code="600001.SH",
            open=10.0,
            high=9.5,
            low=9.8,
            close=10.2,
            pre_close=10.0,
            volume=10000,
            amount=102000,
            is_trading=True,
        )


def test_daily_bar_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        DailyBar(
            trade_date="2026-03-26",
            ts_code="600001.SH",
            open=-1.0,
            high=10.5,
            low=9.8,
            close=10.2,
            pre_close=10.0,
            volume=10000,
            amount=102000,
            is_trading=True,
        )


def test_financial_summary_rejects_publish_before_report() -> None:
    with pytest.raises(ValidationError, match="publish_date"):
        FinancialSummary(
            report_date="2025-12-31",
            publish_date="2025-12-30",
            ts_code="600001.SH",
            revenue_yoy=None,
            profit_yoy=None,
            net_profit_yoy=None,
            roe=None,
            gross_margin=None,
            debt_to_asset=None,
            operating_cashflow_to_profit=None,
            goodwill_to_equity=None,
        )


def test_announcement_event_rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        AnnouncementEvent(
            event_time="2026-03-26T09:30:00",
            ts_code="600001.SH",
            title="Sample event",
            source="sample_notice",
            event_type="buyback",
            event_direction="upward",
            event_strength=0.5,
            event_risk_level="low",
            raw_text=None,
        )
