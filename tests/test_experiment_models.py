from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.experiments import ExperimentArtifact, ExperimentIndex, ExperimentMetric, ExperimentRecord


def test_experiment_record_valid() -> None:
    record = _record()

    assert record.status == "SUCCESS"
    assert record.metrics[0].name == "total_return"


def test_experiment_record_invalid_status_fails() -> None:
    with pytest.raises(ValidationError):
        _record(status="UNKNOWN")


def test_experiment_artifact_invalid_type_fails() -> None:
    with pytest.raises(ValidationError):
        ExperimentArtifact(name="x", path="x.bin", artifact_type="binary")


def test_experiment_index_serializes() -> None:
    index = ExperimentIndex(registry_dir="outputs/experiments", generated_at=datetime(2026, 1, 1), experiments=[_record()])

    payload = index.model_dump(mode="json")
    assert payload["experiments"][0]["experiment_id"] == "exp_20260101_000000_abcdef12"


def _record(status: str = "SUCCESS") -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id="exp_20260101_000000_abcdef12",
        created_at=datetime(2026, 1, 1),
        command="run-backtest",
        command_args={"start": "2026-01-05"},
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        output_dir="outputs/backtests/x",
        data_source="local_csv",
        data_version="sample",
        config_hash="a" * 64,
        code_version=None,
        status=status,
        metrics=[ExperimentMetric(name="total_return", value=0.1, category="backtest")],
        artifacts=[ExperimentArtifact(name="metrics.json", path="outputs/backtests/x/metrics.json", artifact_type="json")],
        notes="note",
        tags=["mvp"],
    )
