from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.probability import ProbabilityDatasetBuilder


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def test_sample_data_builds_probability_dataset() -> None:
    records = _builder().build_dataset(date(2026, 1, 5), date(2026, 3, 20))

    assert records
    assert all(record.ts_code for record in records)


def test_include_only_universe_allowed_excludes_blocked_stocks() -> None:
    records = _builder().build_dataset(date(2026, 3, 20), date(2026, 3, 24))

    assert records
    assert all(record.universe_allowed for record in records)


def test_include_only_computable_factors_excludes_uncomputable_rows() -> None:
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    strict_records = ProbabilityDatasetBuilder(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).build_dataset(date(2026, 1, 5), date(2026, 1, 7))
    loose_probability = config.probability.model_copy(update={"include_only_computable_factors": False})
    loose_config = config.model_copy(update={"probability": loose_probability})
    loose_records = ProbabilityDatasetBuilder(
        loose_config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).build_dataset(date(2026, 1, 5), date(2026, 1, 7))

    assert len(loose_records) >= len(strict_records)


def test_trainable_requires_at_least_one_horizon_label() -> None:
    records = _builder().build_dataset(date(2026, 4, 8), date(2026, 4, 9))

    assert any(not record.is_trainable for record in records)
    assert all(record.missing_reasons for record in records if not record.is_trainable)


def test_features_use_trade_date_close_not_future_close() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    bars = adapter.load_daily_bars()
    records = _builder().build_dataset(date(2026, 3, 20), date(2026, 3, 21))
    record = records[0]
    same_day_bar = next(bar for bar in bars if bar.ts_code == record.ts_code and bar.trade_date == record.trade_date)

    assert record.latest_close == same_day_bar.close
    assert record.future_return_5d is not None


def test_future_return_fields_are_labels() -> None:
    record = _builder().build_dataset(date(2026, 3, 20), date(2026, 3, 21))[0]

    assert record.future_return_5d is None or isinstance(record.future_return_5d, float)
    assert 0 <= record.stock_score <= 100


def _builder() -> ProbabilityDatasetBuilder:
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    return ProbabilityDatasetBuilder(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    )
