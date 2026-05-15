from __future__ import annotations

from datetime import date

from ashare_alpha.data import FinancialSummary
from ashare_alpha.scoring.components import clamp_score
from ashare_alpha.scoring.models import FundamentalScoreResult


def latest_financial_by_code(
    financial_summary: list[FinancialSummary],
    trade_date: date,
) -> dict[str, FinancialSummary]:
    usable = [item for item in financial_summary if item.publish_date <= trade_date]
    latest: dict[str, FinancialSummary] = {}
    for item in sorted(usable, key=lambda row: (row.publish_date, row.report_date)):
        latest[item.ts_code] = item
    return latest


def score_fundamental_quality(financial: FinancialSummary | None) -> FundamentalScoreResult:
    if financial is None:
        return FundamentalScoreResult(score=50.0, reasons=["无可用财务数据，基本面质量使用中性分"])

    score = 60.0
    reasons: list[str] = []
    risk_reasons: list[str] = []

    if financial.revenue_yoy is not None:
        if financial.revenue_yoy > 0:
            score += 10
            reasons.append("收入同比增长")
        elif financial.revenue_yoy < 0:
            score -= 10
            risk_reasons.append("收入同比为负")
    if financial.net_profit_yoy is not None:
        if financial.net_profit_yoy > 0:
            score += 15
            reasons.append("净利润同比增长")
        elif financial.net_profit_yoy < 0:
            score -= 20
            risk_reasons.append("净利润同比为负")
    if _ratio(financial.roe) is not None and _ratio(financial.roe) > 0.10:
        score += 10
        reasons.append("ROE较好")
    if _ratio(financial.gross_margin) is not None and _ratio(financial.gross_margin) > 0.20:
        score += 5
        reasons.append("毛利率较好")
    if financial.operating_cashflow_to_profit is not None:
        if financial.operating_cashflow_to_profit > 0.8:
            score += 10
            reasons.append("经营现金流质量较好")
        elif financial.operating_cashflow_to_profit < 0:
            score -= 20
            risk_reasons.append("经营现金流质量较差")
    if _ratio(financial.debt_to_asset) is not None and _ratio(financial.debt_to_asset) > 0.70:
        score -= 20
        risk_reasons.append("资产负债率较高")
    if _ratio(financial.goodwill_to_equity) is not None and _ratio(financial.goodwill_to_equity) > 0.30:
        score -= 20
        risk_reasons.append("商誉占净资产比例较高")

    return FundamentalScoreResult(score=clamp_score(score), reasons=reasons, risk_reasons=risk_reasons)


def _ratio(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) > 2:
        return value / 100
    return value
