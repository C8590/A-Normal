from __future__ import annotations

from datetime import date

from ashare_alpha.data import FinancialSummary
from ashare_alpha.scoring import latest_financial_by_code, score_fundamental_quality


TRADE_DATE = date(2026, 3, 20)


def test_latest_financial_uses_publish_date_before_trade_date() -> None:
    rows = [
        _financial("600001.SH", publish_date=date(2026, 3, 18), net_profit_yoy=1),
        _financial("600001.SH", publish_date=date(2026, 3, 20), net_profit_yoy=2),
    ]

    latest = latest_financial_by_code(rows, TRADE_DATE)

    assert latest["600001.SH"].net_profit_yoy == 2


def test_future_financial_is_not_used() -> None:
    rows = [
        _financial("600001.SH", publish_date=date(2026, 3, 18), net_profit_yoy=1),
        _financial("600001.SH", publish_date=date(2026, 3, 21), net_profit_yoy=99),
    ]

    latest = latest_financial_by_code(rows, TRADE_DATE)

    assert latest["600001.SH"].net_profit_yoy == 1


def test_positive_profit_growth_adds_score() -> None:
    result = score_fundamental_quality(_financial("600001.SH", net_profit_yoy=20))

    assert result.score > 60
    assert "净利润同比增长" in result.reasons


def test_high_debt_deducts_score() -> None:
    result = score_fundamental_quality(_financial("600001.SH", debt_to_asset=82))

    assert "资产负债率较高" in result.risk_reasons


def test_high_goodwill_deducts_score() -> None:
    result = score_fundamental_quality(_financial("600001.SH", goodwill_to_equity=35))

    assert "商誉占净资产比例较高" in result.risk_reasons


def test_missing_financial_returns_50() -> None:
    assert score_fundamental_quality(None).score == 50


def _financial(
    ts_code: str,
    publish_date: date = TRADE_DATE,
    revenue_yoy: float | None = 10,
    net_profit_yoy: float | None = 10,
    debt_to_asset: float | None = 30,
    goodwill_to_equity: float | None = 5,
) -> FinancialSummary:
    return FinancialSummary(
        report_date=date(2025, 12, 31),
        publish_date=publish_date,
        ts_code=ts_code,
        revenue_yoy=revenue_yoy,
        profit_yoy=net_profit_yoy,
        net_profit_yoy=net_profit_yoy,
        roe=12,
        gross_margin=30,
        debt_to_asset=debt_to_asset,
        operating_cashflow_to_profit=1.0,
        goodwill_to_equity=goodwill_to_equity,
    )
