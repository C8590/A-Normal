from __future__ import annotations

from datetime import date

from ashare_alpha.scoring import compute_market_regime
from tests_support import factor, universe


TRADE_DATE = date(2026, 3, 20)


def test_strong_market_regime() -> None:
    factors = [
        factor("600001.SH", close_above_ma20=True, close_above_ma60=True, momentum_20d=0.05),
        factor("600002.SH", close_above_ma20=True, close_above_ma60=True, momentum_20d=0.03),
        factor("600003.SH", close_above_ma20=True, close_above_ma60=False, momentum_20d=0.01),
    ]
    result = compute_market_regime(factors, [universe(item.ts_code) for item in factors])

    assert result.regime == "strong"
    assert result.score == 90


def test_weak_market_regime() -> None:
    factors = [
        factor("600001.SH", close_above_ma20=True, close_above_ma60=False, momentum_20d=0.01),
        factor("600002.SH", close_above_ma20=False, close_above_ma60=False, momentum_20d=0.01),
        factor("600003.SH", close_above_ma20=False, close_above_ma60=False, momentum_20d=0.01),
    ]
    result = compute_market_regime(factors, [universe(item.ts_code) for item in factors])

    assert result.regime == "weak"


def test_risk_market_regime() -> None:
    factors = [
        factor("600001.SH", close_above_ma20=False, close_above_ma60=False, momentum_20d=-0.05),
        factor("600002.SH", close_above_ma20=False, close_above_ma60=False, momentum_20d=-0.03),
        factor("600003.SH", close_above_ma20=False, close_above_ma60=False, momentum_20d=-0.01),
    ]
    result = compute_market_regime(factors, [universe(item.ts_code) for item in factors])

    assert result.regime == "risk"


def test_insufficient_computable_stocks_returns_neutral() -> None:
    result = compute_market_regime([factor("600001.SH")], [universe("600001.SH")])

    assert result.regime == "neutral"
    assert result.score == 50
    assert "可计算股票数量不足" in result.reason
