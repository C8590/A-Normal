from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.sweeps.models import SweepResult, SweepRunRecord, SweepSpec


def test_sweep_spec_valid() -> None:
    spec = SweepSpec.model_validate(
        {
            "sweep_name": "demo",
            "command": "run-pipeline",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": "outputs/sweeps",
            "experiment_registry_dir": "outputs/experiments",
            "variants": [{"name": "buy_80", "config_overrides": {}}],
        }
    )

    assert spec.sweep_name == "demo"
    assert spec.variants[0].name == "buy_80"


def test_sweep_spec_rejects_invalid_command() -> None:
    with pytest.raises(ValidationError):
        SweepSpec.model_validate(
            {
                "sweep_name": "demo",
                "command": "scrape-web",
                "base_config_dir": "configs/ashare_alpha",
                "output_root_dir": "outputs/sweeps",
                "experiment_registry_dir": "outputs/experiments",
                "variants": [{"name": "ok"}],
            }
        )


def test_sweep_spec_rejects_empty_variants() -> None:
    with pytest.raises(ValidationError):
        SweepSpec.model_validate(
            {
                "sweep_name": "demo",
                "command": "run-pipeline",
                "base_config_dir": "configs/ashare_alpha",
                "output_root_dir": "outputs/sweeps",
                "experiment_registry_dir": "outputs/experiments",
                "variants": [],
            }
        )


def test_sweep_variant_rejects_invalid_name() -> None:
    with pytest.raises(ValidationError):
        SweepSpec.model_validate(
            {
                "sweep_name": "demo",
                "command": "run-pipeline",
                "base_config_dir": "configs/ashare_alpha",
                "output_root_dir": "outputs/sweeps",
                "experiment_registry_dir": "outputs/experiments",
                "variants": [{"name": "bad name"}],
            }
        )


def test_sweep_result_serializes() -> None:
    now = datetime.now()
    result = SweepResult(
        sweep_id="sweep_1",
        sweep_name="demo",
        command="run-backtest",
        generated_at=now,
        base_config_dir="configs/ashare_alpha",
        output_dir="outputs/sweeps/sweep_1",
        registry_dir="outputs/experiments",
        total_variants=1,
        success_count=1,
        partial_count=0,
        failed_count=0,
        runs=[
            SweepRunRecord(
                variant_name="v1",
                status="SUCCESS",
                experiment_id="exp_1",
                config_dir="config",
                output_dir="output",
                metrics={"total_return": 0.1},
                started_at=now,
                finished_at=now,
                duration_seconds=0.1,
            )
        ],
        summary="ok",
    )

    payload = result.model_dump(mode="json")
    assert payload["runs"][0]["metrics"]["total_return"] == 0.1
