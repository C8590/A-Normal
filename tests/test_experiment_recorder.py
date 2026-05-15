from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.experiments import (
    ExperimentRecorder,
    ExperimentRegistry,
    discover_artifacts,
    extract_metrics_from_output,
    infer_data_version_from_dir,
)


def test_infer_data_version_from_import_dir() -> None:
    assert infer_data_version_from_dir(Path("data/imports/vendor/v1")) == ("vendor", "v1")


def test_infer_data_version_from_materialized_dir() -> None:
    assert infer_data_version_from_dir(Path("data/materialized/vendor/v2")) == ("vendor", "v2")


def test_infer_data_version_from_sample_dir() -> None:
    assert infer_data_version_from_dir(Path("data/sample/ashare_alpha")) == ("local_csv", "sample")


def test_discover_artifacts_finds_csv_json_md(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "a.csv").write_text("", encoding="utf-8")
    (output_dir / "b.json").write_text("{}", encoding="utf-8")
    (output_dir / "c.md").write_text("# c", encoding="utf-8")

    types = {artifact.artifact_type for artifact in discover_artifacts(output_dir)}
    assert {"csv", "json", "markdown"} <= types


def test_extract_metrics_from_backtest_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "backtest"
    output_dir.mkdir()
    _write_json(output_dir / "metrics.json", {"total_return": 0.1, "sharpe": 1.2, "trade_count": 3})

    metrics = extract_metrics_from_output(output_dir, "run-backtest")

    assert {metric.name: metric.value for metric in metrics}["total_return"] == 0.1


def test_extract_metrics_from_pipeline_manifest(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline"
    output_dir.mkdir()
    _write_json(output_dir / "manifest.json", {"total_stocks": 12, "buy_count": 1})

    metrics = extract_metrics_from_output(output_dir, "run-pipeline")

    assert {metric.name: metric.value for metric in metrics}["buy_count"] == 1


def test_extract_metrics_from_probability_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "probability"
    output_dir.mkdir()
    _write_json(output_dir / "metrics.json", [{"horizon": 5, "auc": 0.7, "brier_score": 0.2}])

    metrics = extract_metrics_from_output(output_dir, "train-probability-model")

    assert {metric.name: metric.value for metric in metrics}["auc_5d"] == 0.7


def test_record_completed_run_saves_record(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    _write_json(output_dir / "manifest.json", {"total_stocks": 12})
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "a.yaml").write_text("x: 1\n", encoding="utf-8")
    registry = ExperimentRegistry(tmp_path / "registry")

    record = ExperimentRecorder(registry).record_completed_run(
        command="run-pipeline",
        command_args={"date": "2026-03-20"},
        status="SUCCESS",
        output_dir=output_dir,
        data_dir=Path("data/sample/ashare_alpha"),
        config_dir=config_dir,
        tags=["mvp"],
    )

    assert registry.get(record.experiment_id).data_version == "sample"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
