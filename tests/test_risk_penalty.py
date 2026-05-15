from __future__ import annotations

from ashare_alpha.config import load_project_config
from ashare_alpha.events import EventDailyRecord
from ashare_alpha.scoring import calculate_risk_penalty
from ashare_alpha.scoring.models import FundamentalScoreResult
from tests_support import factor, universe


def test_high_event_risk_score_adds_penalty() -> None:
    result = calculate_risk_penalty(
        load_project_config(),
        universe("600001.SH"),
        factor("600001.SH"),
        _event(event_risk_score=90),
        FundamentalScoreResult(score=60),
    )

    assert result.risk_penalty_score >= 40
    assert "公告事件风险分较高" in result.risk_reasons


def test_low_liquidity_adds_penalty() -> None:
    result = calculate_risk_penalty(
        load_project_config(),
        universe("600001.SH", liquidity_score=30),
        factor("600001.SH"),
        _event(),
        FundamentalScoreResult(score=60),
    )

    assert "流动性评分偏低" in result.risk_reasons


def test_limit_down_adds_penalty() -> None:
    result = calculate_risk_penalty(
        load_project_config(),
        universe("600001.SH"),
        factor("600001.SH", limit_down_recent_count=1),
        _event(),
        FundamentalScoreResult(score=60),
    )

    assert "近窗口出现跌停" in result.risk_reasons


def test_risk_penalty_is_clamped_to_100() -> None:
    result = calculate_risk_penalty(
        load_project_config(),
        universe("600001.SH", risk_score=100, liquidity_score=0),
        factor("600001.SH", volatility_20d=0.10, limit_down_recent_count=5),
        _event(event_risk_score=90),
        FundamentalScoreResult(
            score=10,
            risk_reasons=["资产负债率较高", "商誉占净资产比例较高", "净利润同比为负", "经营现金流质量较差"],
        ),
    )

    assert result.risk_penalty_score == 100


def _event(event_risk_score: float = 0) -> EventDailyRecord:
    return EventDailyRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        event_score=0,
        event_risk_score=event_risk_score,
        event_count=1,
        positive_event_count=0,
        negative_event_count=0,
        high_risk_event_count=0,
        event_block_buy=False,
        block_buy_reasons=[],
        latest_event_title=None,
        latest_negative_event_title=None,
        event_reason="近窗口内无有效公告事件",
    )
