from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.probability import split_dataset_by_time
from ashare_alpha.probability.models import ProbabilityDatasetRecord


def test_split_by_time_train_dates_before_test_dates() -> None:
    records = [_record(date(2026, 1, 1) + timedelta(days=index)) for index in range(10)]

    train, test = split_dataset_by_time(records, 0.7, 2, purge_gap=False)

    assert max(record.trade_date for record in train) < min(record.trade_date for record in test)


def test_purge_gap_removes_last_training_dates() -> None:
    records = [_record(date(2026, 1, 1) + timedelta(days=index)) for index in range(10)]

    train_no_purge, _ = split_dataset_by_time(records, 0.7, 2, purge_gap=False)
    train_purge, _ = split_dataset_by_time(records, 0.7, 2, purge_gap=True)

    assert len(train_purge) == len(train_no_purge) - 2


def test_split_too_few_dates_does_not_crash() -> None:
    train, test = split_dataset_by_time([_record(date(2026, 1, 1))], 0.7, 2, purge_gap=True)

    assert train
    assert test == []


def _record(trade_date: date) -> ProbabilityDatasetRecord:
    return ProbabilityDatasetRecord(
        trade_date=trade_date,
        ts_code="600001.SH",
        symbol="600001",
        name="测试",
        industry="工业",
        stock_score=70,
        raw_score=70,
        risk_penalty_score=0,
        market_regime_score=60,
        industry_strength_score=60,
        trend_momentum_score=60,
        fundamental_quality_score=60,
        liquidity_score=60,
        event_component_score=60,
        volatility_control_score=60,
        event_score=0,
        event_risk_score=0,
        universe_allowed=True,
        signal="WATCH",
        risk_level="low",
        latest_close=10,
        future_return_5d=0.01,
        y_win_5d=1,
        is_trainable=True,
        missing_reasons=[],
    )
