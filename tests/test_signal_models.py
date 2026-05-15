from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from ashare_alpha.signals import SignalDailyRecord


def test_signal_daily_record_validates() -> None:
    record = _record()

    assert record.signal == "WATCH"
    assert record.reason


def test_stock_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        _record(stock_score=101)


def test_buy_requires_positive_target_weight() -> None:
    with pytest.raises(ValidationError, match="target_weight"):
        _record(signal="BUY", target_weight=0, target_shares=100, buy_reasons=["综合评分较高"])


def test_block_requires_zero_target_weight() -> None:
    with pytest.raises(ValidationError, match="target_weight"):
        _record(signal="BLOCK", target_weight=0.1, target_shares=0, risk_reasons=["风险阻断"])


def test_reason_must_not_be_empty() -> None:
    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        _record(reason="")


def _record(**overrides) -> SignalDailyRecord:
    payload = {
        "trade_date": date(2026, 3, 20),
        "ts_code": "600001.SH",
        "symbol": "600001",
        "name": "Alpha",
        "exchange": "sse",
        "board": "main",
        "industry": "industrial",
        "universe_allowed": True,
        "universe_exclude_reasons": [],
        "universe_exclude_reason_text": None,
        "market_regime": "neutral",
        "market_regime_score": 65,
        "industry_strength_score": 50,
        "trend_momentum_score": 70,
        "fundamental_quality_score": 70,
        "liquidity_score": 80,
        "event_component_score": 50,
        "volatility_control_score": 70,
        "raw_score": 65,
        "risk_penalty_score": 0,
        "stock_score": 65,
        "event_score": 0,
        "event_risk_score": 0,
        "event_block_buy": False,
        "event_reason": None,
        "risk_score": 0,
        "risk_level": "low",
        "signal": "WATCH",
        "target_weight": 0,
        "target_shares": 0,
        "estimated_position_value": 0,
        "buy_reasons": [],
        "risk_reasons": [],
        "reason": "WATCH：综合评分 65.0，风险等级 low",
    }
    payload.update(overrides)
    return SignalDailyRecord(**payload)
