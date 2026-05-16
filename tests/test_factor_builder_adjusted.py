from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.config import load_project_config
from ashare_alpha.data.realism.models import AdjustmentFactorRecord
from ashare_alpha.factors import FactorBuilder, FactorMissingReason
from tests.tests_support import daily_bar


def test_raw_factor_builder_matches_existing_logic() -> None:
    bars = _bars()

    record = FactorBuilder(load_project_config(), bars, price_source="raw").build_for_date(_target_date())[0]

    assert record.price_source == "raw"
    assert record.adjusted_used is False
    assert record.momentum_5d == 0.0


def test_qfq_factor_builder_uses_adjusted_close_for_momentum() -> None:
    bars = _bars()

    record = FactorBuilder(
        load_project_config(),
        bars,
        price_source="qfq",
        adjustment_factors=_factors(),
    ).build_for_date(_target_date())[0]

    assert record.price_source == "qfq"
    assert record.adjusted_used is True
    assert record.momentum_5d == 1.0
    assert record.latest_close == 100.0


def test_hfq_factor_builder_uses_adjusted_close_for_momentum() -> None:
    bars = _bars()

    record = FactorBuilder(
        load_project_config(),
        bars,
        price_source="hfq",
        adjustment_factors=_factors(adj_type="hfq"),
    ).build_for_date(_target_date())[0]

    assert record.price_source == "hfq"
    assert record.adjusted_used is True
    assert record.momentum_5d == 1.0


def test_missing_adjusted_factor_sets_missing_reason_without_crashing() -> None:
    bars = _bars()
    factors = _factors()[:-1]

    record = FactorBuilder(
        load_project_config(),
        bars,
        price_source="qfq",
        adjustment_factors=factors,
    ).build_for_date(_target_date())[0]

    assert record.is_computable is False
    assert FactorMissingReason.ADJUSTED_PRICE_UNAVAILABLE in record.missing_reasons
    assert FactorMissingReason.ADJUSTED_FACTOR_MISSING in record.missing_reasons


def test_adjusted_factor_builder_does_not_use_future_adjustment_data() -> None:
    bars = _bars()
    factors = _factors()
    future_date = _target_date() + timedelta(days=1)
    future_bar = daily_bar(
        trade_date=future_date.isoformat(),
        open=1000.0,
        high=1000.0,
        low=1000.0,
        close=1000.0,
        pre_close=1000.0,
    )
    future_factor = AdjustmentFactorRecord(
        ts_code="600001.SH",
        trade_date=future_date,
        adj_factor=99.0,
        adj_type="qfq",
        source_name="pytest",
        available_at=f"{future_date.isoformat()}T18:00:00",
    )

    without_future = FactorBuilder(
        load_project_config(),
        bars,
        price_source="qfq",
        adjustment_factors=factors,
    ).build_for_date(_target_date())[0]
    with_future = FactorBuilder(
        load_project_config(),
        [*bars, future_bar],
        price_source="qfq",
        adjustment_factors=[*factors, future_factor],
    ).build_for_date(_target_date())[0]

    assert with_future.latest_close == without_future.latest_close
    assert with_future.momentum_5d == without_future.momentum_5d


def test_adjusted_builder_keeps_amount_and_limit_statistics_on_raw_data() -> None:
    bars = _bars()
    bars[-6] = bars[-6].model_copy(update={"limit_up": 100.0})

    record = FactorBuilder(
        load_project_config(),
        bars,
        price_source="qfq",
        adjustment_factors=_factors(),
    ).build_for_date(_target_date())[0]

    assert record.amount_mean_20d == 999.0
    assert record.limit_up_recent_count == 1


def _target_date() -> date:
    return date(2026, 3, 10)


def _bars() -> list:
    start = _target_date() - timedelta(days=64)
    return [
        daily_bar(
            trade_date=(start + timedelta(days=index)).isoformat(),
            close=100.0,
            open=100.0,
            high=100.0,
            low=100.0,
            pre_close=100.0,
            amount=999.0,
            turnover_rate=1.0,
            limit_up=110.0,
            limit_down=90.0,
        )
        for index in range(65)
    ]


def _factors(adj_type: str = "qfq") -> list[AdjustmentFactorRecord]:
    start = _target_date() - timedelta(days=64)
    records = []
    for index in range(65):
        trade_date = start + timedelta(days=index)
        records.append(
            AdjustmentFactorRecord(
                ts_code="600001.SH",
                trade_date=trade_date,
                adj_factor=1.0 if index < 60 else 2.0,
                adj_type=adj_type,
                source_name="pytest",
                available_at=f"{trade_date.isoformat()}T18:00:00",
            )
        )
    return records
