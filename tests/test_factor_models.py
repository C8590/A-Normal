from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.factors import FactorDailyRecord


def test_factor_daily_record_validates() -> None:
    record = FactorDailyRecord(
        trade_date="2026-03-20",
        ts_code="600001.SH",
        latest_close=12.0,
        latest_open=11.8,
        latest_high=12.2,
        latest_low=11.7,
        latest_amount=12000000,
        latest_turnover_rate=1.2,
        return_1d=0.01,
        momentum_5d=0.05,
        momentum_20d=0.1,
        momentum_60d=0.2,
        ma20=11.0,
        ma60=10.0,
        close_above_ma20=True,
        close_above_ma60=True,
        volatility_20d=0.02,
        max_drawdown_20d=-0.03,
        amount_mean_20d=10000000,
        turnover_mean_20d=1.0,
        limit_up_recent_count=1,
        limit_down_recent_count=0,
        trading_days_used=80,
        is_computable=True,
        missing_reasons=[],
        missing_reason_text="",
    )

    assert record.is_computable is True


def test_non_computable_record_requires_missing_reason() -> None:
    with pytest.raises(ValidationError, match="missing_reasons"):
        FactorDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            limit_up_recent_count=0,
            limit_down_recent_count=0,
            trading_days_used=0,
            is_computable=False,
            missing_reasons=[],
            missing_reason_text="",
        )


def test_volatility_must_not_be_negative() -> None:
    with pytest.raises(ValidationError):
        FactorDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            volatility_20d=-0.01,
            limit_up_recent_count=0,
            limit_down_recent_count=0,
            trading_days_used=80,
            is_computable=True,
        )


def test_max_drawdown_must_not_be_positive() -> None:
    with pytest.raises(ValidationError):
        FactorDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            max_drawdown_20d=0.01,
            limit_up_recent_count=0,
            limit_down_recent_count=0,
            trading_days_used=80,
            is_computable=True,
        )


def test_limit_up_count_must_not_be_negative() -> None:
    with pytest.raises(ValidationError):
        FactorDailyRecord(
            trade_date="2026-03-20",
            ts_code="600001.SH",
            limit_up_recent_count=-1,
            limit_down_recent_count=0,
            trading_days_used=80,
            is_computable=True,
        )
