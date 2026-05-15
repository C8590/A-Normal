from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.pipeline import PipelineManifest, PipelineStepResult


def test_pipeline_step_result_validates() -> None:
    step = PipelineStepResult(
        name="validate_data",
        status="SUCCESS",
        started_at=datetime(2026, 3, 20, 9, 0),
        finished_at=datetime(2026, 3, 20, 9, 0, 1),
        duration_seconds=1.0,
        output_paths=[],
        summary={"passed": True},
        error_message=None,
    )

    assert step.status == "SUCCESS"


def test_failed_step_requires_error_message() -> None:
    with pytest.raises(ValidationError, match="error_message"):
        PipelineStepResult(
            name="validate_data",
            status="FAILED",
            started_at=datetime(2026, 3, 20, 9, 0),
            finished_at=datetime(2026, 3, 20, 9, 0, 1),
            duration_seconds=1.0,
            output_paths=[],
            summary={},
            error_message=None,
        )


def test_pipeline_manifest_validates_and_serializes_dates() -> None:
    manifest = PipelineManifest(
        pipeline_date=date(2026, 3, 20),
        generated_at=datetime(2026, 3, 20, 9, 0),
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        output_dir="outputs/pipelines/pipeline_2026-03-20",
        model_dir=None,
        status="SUCCESS",
        steps=[],
        total_stocks=12,
        allowed_universe_count=3,
        buy_count=0,
        watch_count=3,
        block_count=9,
        high_risk_count=2,
        market_regime="strong",
        probability_predictable_count=None,
        daily_report_path=None,
        universe_csv_path=None,
        factor_csv_path=None,
        event_csv_path=None,
        signal_csv_path=None,
        probability_csv_path=None,
    )
    payload = manifest.model_dump(mode="json")

    assert payload["pipeline_date"] == "2026-03-20"
    assert payload["generated_at"] == "2026-03-20T09:00:00"
