from __future__ import annotations

from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.data import DailyBar
from ashare_alpha.universe import UniverseDailyRecord


def factor(ts_code: str = "600001.SH", **overrides) -> FactorDailyRecord:
    payload = {
        "trade_date": "2026-03-20",
        "ts_code": ts_code,
        "latest_close": 10.0,
        "latest_open": 9.8,
        "latest_high": 10.2,
        "latest_low": 9.7,
        "latest_amount": 100000000.0,
        "latest_turnover_rate": 1.0,
        "return_1d": 0.01,
        "momentum_5d": 0.02,
        "momentum_20d": 0.03,
        "momentum_60d": 0.04,
        "ma20": 9.0,
        "ma60": 8.0,
        "close_above_ma20": True,
        "close_above_ma60": True,
        "volatility_20d": 0.015,
        "max_drawdown_20d": -0.03,
        "amount_mean_20d": 100000000.0,
        "turnover_mean_20d": 1.0,
        "limit_up_recent_count": 0,
        "limit_down_recent_count": 0,
        "trading_days_used": 60,
        "is_computable": True,
        "missing_reasons": [],
        "missing_reason_text": "",
    }
    payload.update(overrides)
    return FactorDailyRecord(**payload)


def universe(ts_code: str = "600001.SH", **overrides) -> UniverseDailyRecord:
    payload = {
        "trade_date": "2026-03-20",
        "ts_code": ts_code,
        "symbol": ts_code[:6],
        "name": ts_code,
        "exchange": "sse",
        "board": "main",
        "industry": "industrial",
        "is_allowed": True,
        "exclude_reasons": [],
        "exclude_reason_text": "",
        "listing_days": 3000,
        "latest_close": 10.0,
        "one_lot_value": 1000.0,
        "avg_amount_20d": 100000000.0,
        "trading_days_20d": 20,
        "liquidity_score": 80.0,
        "risk_score": 0.0,
        "has_recent_negative_event": False,
        "recent_negative_event_count": 0,
        "latest_negative_event_title": None,
    }
    payload.update(overrides)
    return UniverseDailyRecord(**payload)


def daily_bar(ts_code: str = "600001.SH", trade_date: str = "2026-03-20", **overrides) -> DailyBar:
    payload = {
        "trade_date": trade_date,
        "ts_code": ts_code,
        "open": 10.0,
        "high": 10.2,
        "low": 9.8,
        "close": 10.0,
        "pre_close": 10.0,
        "volume": 100000.0,
        "amount": 1000000.0,
        "turnover_rate": 1.0,
        "limit_up": 11.0,
        "limit_down": 9.0,
        "is_trading": True,
    }
    payload.update(overrides)
    return DailyBar(**payload)
