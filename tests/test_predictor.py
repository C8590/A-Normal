from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.probability import ProbabilityPredictor, ProbabilityTrainer


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def test_predictor_can_predict_for_date() -> None:
    predictions = _predictions()

    assert predictions


def test_predictions_are_sorted_by_ts_code() -> None:
    predictions = _predictions()

    assert [item.ts_code for item in predictions] == sorted(item.ts_code for item in predictions)


def test_universe_blocked_stock_has_clear_unpredictable_reason() -> None:
    blocked = next(item for item in _predictions() if item.ts_code == "300001.SZ")

    assert blocked.is_predictable is False
    assert blocked.reason


def test_probability_fields_are_between_zero_and_one() -> None:
    for prediction in _predictions():
        for value in (prediction.p_win_5d, prediction.p_win_10d, prediction.p_win_20d):
            if value is not None:
                assert 0 <= value <= 1


def _predictions():
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    trainer = ProbabilityTrainer(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    )
    result = trainer.train(date(2026, 1, 5), date(2026, 3, 20))
    return ProbabilityPredictor(
        config,
        result.model,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).predict_for_date(date(2026, 3, 20))
