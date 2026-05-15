from __future__ import annotations

from ashare_alpha.events import EventDailyRecord
from ashare_alpha.scoring import event_component_score, score_trend_momentum, score_volatility_control
from tests_support import factor


def test_positive_trend_momentum_adds_score() -> None:
    result = score_trend_momentum(
        factor(momentum_5d=0.01, momentum_20d=0.02, momentum_60d=0.03, close_above_ma20=True, close_above_ma60=True)
    )

    assert result.score > 50


def test_negative_trend_momentum_deducts_score() -> None:
    result = score_trend_momentum(
        factor(momentum_5d=-0.01, momentum_20d=-0.02, momentum_60d=-0.03, close_above_ma20=False, close_above_ma60=False)
    )

    assert result.score < 50


def test_high_volatility_deducts_score() -> None:
    result = score_volatility_control(factor(volatility_20d=0.08))

    assert result.score < 70
    assert "20日波动率较高" in result.risk_reasons


def test_large_drawdown_deducts_score() -> None:
    result = score_volatility_control(factor(max_drawdown_20d=-0.20))

    assert result.score < 70
    assert "20日最大回撤较大" in result.risk_reasons


def test_event_score_maps_to_component_score() -> None:
    event = EventDailyRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        event_score=40,
        event_risk_score=0,
        event_count=1,
        positive_event_count=1,
        negative_event_count=0,
        high_risk_event_count=0,
        event_block_buy=False,
        block_buy_reasons=[],
        latest_event_title="回购",
        latest_negative_event_title=None,
        event_reason="正向事件",
    )

    assert event_component_score(event).score == 70
