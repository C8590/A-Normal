from __future__ import annotations

from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.scoring.models import MarketRegimeResult
from ashare_alpha.universe import UniverseDailyRecord


MARKET_REGIME_SCORES = {
    "strong": 90.0,
    "neutral": 65.0,
    "weak": 40.0,
    "risk": 20.0,
}


def compute_market_regime(
    factor_records: list[FactorDailyRecord],
    universe_records: list[UniverseDailyRecord],
    min_stock_count: int = 3,
) -> MarketRegimeResult:
    allowed_codes = {record.ts_code for record in universe_records if record.is_allowed}
    usable = [
        record
        for record in factor_records
        if record.ts_code in allowed_codes and record.is_computable and record.latest_close is not None
    ]
    if len(usable) < min_stock_count:
        return MarketRegimeResult(
            regime="neutral",
            score=50.0,
            reason="可计算股票数量不足，使用中性市场状态",
            stock_count=len(usable),
            pct_above_ma20=0.0,
            pct_above_ma60=0.0,
            avg_momentum_20d=None,
            avg_momentum_60d=None,
        )

    pct_above_ma20 = _true_ratio(record.close_above_ma20 for record in usable)
    pct_above_ma60 = _true_ratio(record.close_above_ma60 for record in usable)
    avg_momentum_20d = _average([record.momentum_20d for record in usable if record.momentum_20d is not None])
    avg_momentum_60d = _average([record.momentum_60d for record in usable if record.momentum_60d is not None])

    if pct_above_ma20 < 0.30 and (avg_momentum_20d or 0) < 0:
        regime = "risk"
        reason = "市场状态偏风险，站上20日均线比例低且20日动量为负"
    elif pct_above_ma20 >= 0.65 and pct_above_ma60 >= 0.55 and (avg_momentum_20d or 0) > 0:
        regime = "strong"
        reason = "市场状态较强，多数可投股票站上均线且20日动量为正"
    elif pct_above_ma20 >= 0.45:
        regime = "neutral"
        reason = "市场状态中性，站上20日均线比例尚可"
    else:
        regime = "weak"
        reason = "市场状态偏弱，站上20日均线比例不足"

    return MarketRegimeResult(
        regime=regime,
        score=MARKET_REGIME_SCORES[regime],
        reason=reason,
        stock_count=len(usable),
        pct_above_ma20=pct_above_ma20,
        pct_above_ma60=pct_above_ma60,
        avg_momentum_20d=avg_momentum_20d,
        avg_momentum_60d=avg_momentum_60d,
    )


def _true_ratio(values) -> float:
    items = [value for value in values if value is not None]
    if not items:
        return 0.0
    return sum(1 for value in items if value) / len(items)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
