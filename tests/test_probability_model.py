from __future__ import annotations

from datetime import date, timedelta
from math import isclose

from a_normal.cli import main
from a_normal.data import DailyBar, LocalCsvAdapter
from a_normal.models import build_labeled_samples, train_probability_model


def test_build_labeled_samples_constructs_future_labels_without_leakage():
    bars = make_bars("000001.SZ", start=date(2026, 1, 1), days=25)

    samples = build_labeled_samples(bars)

    assert len(samples) == 5
    first = samples[0]
    assert first.trade_date == date(2026, 1, 1)
    assert isclose(first.future_5d_return, 105 / 100 - 1)
    assert isclose(first.future_10d_return, 110 / 100 - 1)
    assert isclose(first.future_20d_return, 120 / 100 - 1)
    assert first.y_5d_win == 1
    assert first.y_10d_win == 1
    assert "momentum_5d" in first.features


def test_train_probability_model_runs_on_sample_data():
    adapter = LocalCsvAdapter()

    result = train_probability_model(adapter.load_daily_bars(), min_samples=30)

    assert result.status == "ok"
    assert result.sample_count >= 30
    assert result.train_count > 0
    assert result.test_count > 0
    assert result.predictions
    assert "p_5d_win" in result.evaluation
    assert "p_10d_win" in result.evaluation
    for metrics in result.evaluation.values():
        assert 0 <= metrics.accuracy <= 1
        assert 0 <= metrics.precision <= 1
        assert 0 <= metrics.recall <= 1
        assert 0 <= metrics.auc <= 1
        assert "mean_predicted_probability" in metrics.calibration


def test_train_probability_model_reports_insufficient_samples():
    result = train_probability_model(make_bars("000001.SZ", start=date(2026, 1, 1), days=22), min_samples=30)

    assert result.status == "insufficient_samples"
    assert "样本不足" in result.message
    assert result.predictions == ()


def test_cli_train_probability_writes_json(tmp_path, capsys):
    exit_code = main(["train-probability", "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Status:" in captured.out
    assert (tmp_path / "baseline_probability_model.json").exists()


def make_bars(ts_code: str, start: date, days: int) -> list[DailyBar]:
    return [
        DailyBar(
            stock_code=ts_code,
            trade_date=start + timedelta(days=index),
            open=100 + index,
            high=100 + index,
            low=100 + index,
            close=100 + index,
            volume=100000,
            amount=(100 + index) * 100000,
        )
        for index in range(days)
    ]
