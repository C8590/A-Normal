from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.backtest import BacktestEngine
from ashare_alpha.config import load_project_config
from ashare_alpha.data.realism.models import AdjustmentFactorRecord
from ashare_alpha.signals import SignalDailyRecord
from tests.tests_support import daily_bar


class FixedSignalBacktestEngine(BacktestEngine):
    def __init__(self, *args, target_weight: float = 0.1, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.target_weight = target_weight

    def _generate_signals(self, decision_date: date) -> list[SignalDailyRecord]:
        return [
            SignalDailyRecord(
                trade_date=decision_date,
                ts_code="600001.SH",
                symbol="600001",
                name="sample",
                exchange="sse",
                board="main",
                industry="industrial",
                universe_allowed=True,
                market_regime="neutral",
                market_regime_score=50,
                industry_strength_score=50,
                trend_momentum_score=50,
                fundamental_quality_score=50,
                liquidity_score=50,
                event_component_score=50,
                volatility_control_score=50,
                raw_score=80,
                risk_penalty_score=0,
                stock_score=80,
                event_score=0,
                event_risk_score=0,
                event_block_buy=False,
                risk_score=0,
                risk_level="low",
                signal="BUY",
                target_weight=self.target_weight,
                target_shares=100,
                estimated_position_value=1000,
                buy_reasons=["pytest"],
                reason="BUY: pytest",
            )
        ]


def test_qfq_engine_values_daily_equity_with_adjusted_close() -> None:
    result = _engine("qfq", _factors("qfq"), target_weight=0.1).run(date(2026, 1, 1), date(2026, 1, 3))

    jan2 = next(record for record in result.daily_equity if record.trade_date == date(2026, 1, 2))
    filled = next(trade for trade in result.trades if trade.status == "FILLED")
    assert filled.price_source == "qfq"
    assert filled.execution_price_source == "raw"
    assert filled.price is not None and filled.price > 100
    assert jan2.price_source == "qfq"
    assert jan2.valuation_basis == "qfq_adjusted_close"
    assert jan2.market_value == 10_000


def test_hfq_engine_values_daily_equity_with_adjusted_close() -> None:
    result = _engine("hfq", _factors("hfq"), target_weight=0.2).run(date(2026, 1, 1), date(2026, 1, 3))

    jan2 = next(record for record in result.daily_equity if record.trade_date == date(2026, 1, 2))
    assert result.metrics.price_source == "hfq"
    assert jan2.price_source == "hfq"
    assert jan2.market_value == 20_000


def test_adjusted_engine_keeps_limit_up_rejection_on_raw_bar() -> None:
    bars = _bars()
    bars[1] = bars[1].model_copy(update={"open": 110.0, "high": 110.0, "low": 110.0, "close": 110.0, "limit_up": 110.0})
    result = _engine("qfq", _factors("qfq"), bars=bars, target_weight=0.1).run(date(2026, 1, 1), date(2026, 1, 3))

    rejected = next(trade for trade in result.trades if trade.status == "REJECTED")
    assert rejected.execution_price_source == "raw"
    assert rejected.reject_reason is not None


def _engine(
    price_source: str,
    factors: list[AdjustmentFactorRecord],
    target_weight: float,
    bars=None,
) -> FixedSignalBacktestEngine:
    config = load_project_config()
    backtest = config.backtest.model_copy(
        update={
            "initial_cash": 100_000,
            "max_position_weight": 1.0,
            "min_position_value": 0,
            "rebalance_frequency": "daily",
        }
    )
    config = config.model_copy(update={"backtest": backtest})
    return FixedSignalBacktestEngine(
        config,
        [],
        bars or _bars(),
        [],
        [],
        price_source=price_source,
        adjustment_factors=factors,
        target_weight=target_weight,
    )


def _bars():
    start = date(2026, 1, 1)
    return [
        daily_bar(
            trade_date=(start + timedelta(days=index)).isoformat(),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            pre_close=100.0,
            limit_up=110.0,
            limit_down=90.0,
        )
        for index in range(3)
    ]


def _factors(adj_type: str) -> list[AdjustmentFactorRecord]:
    factors = [1.0, 1.0, 2.0] if adj_type == "qfq" else [1.0, 2.0, 2.0]
    return [
        AdjustmentFactorRecord(
            ts_code="600001.SH",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            adj_factor=factor,
            adj_type=adj_type,
            source_name="pytest",
            available_at=f"2026-01-0{index + 1}T18:00:00",
        )
        for index, factor in enumerate(factors)
    ]
