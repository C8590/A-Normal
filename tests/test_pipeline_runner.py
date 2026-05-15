from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.pipeline import PipelineRunner
from ashare_alpha.probability import ProbabilityPredictor, ProbabilityTrainer, save_probability_model_json
from ashare_alpha.signals import SignalGenerator
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.universe import UniverseBuilder


SAMPLE_DATE = date(2026, 3, 20)
START = date(2026, 1, 5)
END = date(2026, 3, 20)
DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_default_sample_pipeline_runs_success(tmp_path: Path) -> None:
    manifest = _runner(tmp_path).run()

    assert manifest.status == "SUCCESS"
    assert _step_status(manifest, "predict_probabilities") == "SKIPPED"


def test_missing_model_dir_skips_probability_and_stays_success(tmp_path: Path) -> None:
    manifest = _runner(tmp_path).run()

    assert manifest.status == "SUCCESS"
    assert _step_status(manifest, "predict_probabilities") == "SKIPPED"


def test_valid_model_dir_runs_probability_step(tmp_path: Path) -> None:
    model_dir = _model_dir(tmp_path)
    manifest = _runner(tmp_path, model_dir=model_dir).run()

    assert manifest.status == "SUCCESS"
    assert _step_status(manifest, "predict_probabilities") == "SUCCESS"
    assert manifest.probability_predictable_count == 3


def test_invalid_model_dir_without_requirement_yields_partial(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, model_dir=tmp_path / "missing").run()

    assert manifest.status == "PARTIAL"
    assert _step_status(manifest, "predict_probabilities") == "FAILED"
    assert manifest.daily_report_path is not None


def test_invalid_model_dir_with_requirement_yields_failed(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, model_dir=tmp_path / "missing", require_probability=True).run()

    assert manifest.status == "FAILED"


def test_missing_data_dir_fails_validation_and_stops(tmp_path: Path) -> None:
    manifest = PipelineRunner(
        date=SAMPLE_DATE,
        data_dir=tmp_path / "missing_data",
        config_dir=CONFIG_DIR,
        output_dir=tmp_path / "pipeline",
    ).run()

    assert manifest.status == "FAILED"
    assert [step.name for step in manifest.steps] == ["validate_data"]


def test_pipeline_outputs_expected_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline"
    manifest = _runner(tmp_path, output_dir=output_dir).run()

    assert manifest.status == "SUCCESS"
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "pipeline_summary.md").exists()
    assert (output_dir / f"universe_daily_{SAMPLE_DATE.isoformat()}.csv").exists()
    assert (output_dir / f"factor_daily_{SAMPLE_DATE.isoformat()}.csv").exists()
    assert (output_dir / f"event_daily_{SAMPLE_DATE.isoformat()}.csv").exists()
    assert (output_dir / f"signal_daily_{SAMPLE_DATE.isoformat()}.csv").exists()
    assert (output_dir / "daily_report" / "daily_report.md").exists()


def test_manifest_contains_research_summary(tmp_path: Path) -> None:
    manifest = _runner(tmp_path).run()

    assert manifest.buy_count == 0
    assert manifest.watch_count == 3
    assert manifest.block_count == 9
    assert manifest.market_regime == "strong"


def test_pipeline_does_not_change_signal_or_probability_logic(tmp_path: Path) -> None:
    model_dir = _model_dir(tmp_path)
    direct_signals = [record.model_dump() for record in _signals(SAMPLE_DATE)]
    direct_predictions = [
        record.model_dump() for record in _probability_predictions(SAMPLE_DATE, model_dir / "model.json")
    ]

    _runner(tmp_path, model_dir=model_dir).run()

    assert [record.model_dump() for record in _signals(SAMPLE_DATE)] == direct_signals
    assert [record.model_dump() for record in _probability_predictions(SAMPLE_DATE, model_dir / "model.json")] == direct_predictions


def _runner(
    tmp_path: Path,
    model_dir: Path | None = None,
    require_probability: bool = False,
    output_dir: Path | None = None,
) -> PipelineRunner:
    return PipelineRunner(
        date=SAMPLE_DATE,
        data_dir=DATA_DIR,
        config_dir=CONFIG_DIR,
        output_dir=output_dir or (tmp_path / "pipeline"),
        model_dir=model_dir,
        require_probability=require_probability,
    )


def _model_dir(tmp_path: Path) -> Path:
    model_dir = tmp_path / "model"
    model_dir.mkdir(exist_ok=True)
    config = load_project_config(CONFIG_DIR)
    adapter = LocalCsvAdapter(DATA_DIR)
    result = ProbabilityTrainer(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).train(START, END)
    save_probability_model_json(result.model, model_dir / "model.json")
    return model_dir


def _signals(trade_date: date):
    config = load_project_config(CONFIG_DIR)
    adapter = LocalCsvAdapter(DATA_DIR)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(config, stock_master, daily_bars, financial_summary, events).build_for_date(trade_date)
    factor_records = FactorBuilder(config, daily_bars, stock_master).build_for_date(trade_date)
    event_records = EventFeatureBuilder(config, events, stock_master).build_for_date(trade_date)
    return SignalGenerator(config, stock_master, financial_summary, universe_records, factor_records, event_records).generate_for_date(trade_date)


def _probability_predictions(trade_date: date, model_path: Path):
    from ashare_alpha.probability import load_probability_model_json

    config = load_project_config(CONFIG_DIR)
    adapter = LocalCsvAdapter(DATA_DIR)
    return ProbabilityPredictor(
        config,
        load_probability_model_json(model_path),
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).predict_for_date(trade_date)


def _step_status(manifest, name: str) -> str:
    return next(step.status for step in manifest.steps if step.name == name)
