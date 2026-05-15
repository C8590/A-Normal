from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.probability import ProbabilityTrainer
from ashare_alpha.signals import SignalGenerator
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.universe import UniverseBuilder


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def test_sample_data_runs_probability_trainer() -> None:
    result = _trainer(load_project_config()).train(date(2026, 1, 5), date(2026, 3, 20))

    assert result.dataset_rows > 0
    assert result.metrics


def test_insufficient_samples_generates_summary_without_crash() -> None:
    config = load_project_config()
    probability = config.probability.model_copy(update={"min_train_samples": 9999})
    result = _trainer(config.model_copy(update={"probability": probability})).train(date(2026, 1, 5), date(2026, 3, 20))

    assert "样本数量不足" in result.summary
    assert all(not item.trained for item in result.model.horizon_models.values())


def test_probability_training_does_not_change_signal_logic() -> None:
    before = [record.model_dump() for record in _signals(date(2026, 3, 20))]

    _trainer(load_project_config()).train(date(2026, 1, 5), date(2026, 3, 20))

    assert [record.model_dump() for record in _signals(date(2026, 3, 20))] == before


def _trainer(config) -> ProbabilityTrainer:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    return ProbabilityTrainer(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    )


def _signals(trade_date: date):
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(config, stock_master, daily_bars, financial_summary, events).build_for_date(trade_date)
    factor_records = FactorBuilder(config, daily_bars, stock_master).build_for_date(trade_date)
    event_records = EventFeatureBuilder(config, events, stock_master).build_for_date(trade_date)
    return SignalGenerator(config, stock_master, financial_summary, universe_records, factor_records, event_records).generate_for_date(trade_date)
