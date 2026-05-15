from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.walkforward.models import WalkForwardFold, WalkForwardResult, WalkForwardSpec


def test_walkforward_spec_valid() -> None:
    spec = WalkForwardSpec.model_validate(
        {
            "name": "wf",
            "command": "run-backtest",
            "data_dir": "data/sample/ashare_alpha",
            "base_config_dir": "configs/ashare_alpha",
            "output_root_dir": "outputs/walkforward",
            "experiment_registry_dir": "outputs/experiments",
            "start_date": "2026-01-05",
            "end_date": "2026-03-20",
            "test_window_days": 21,
            "step_days": 14,
            "min_test_trading_days": 5,
        }
    )

    assert spec.name == "wf"
    assert spec.command == "run-backtest"


def test_walkforward_spec_rejects_start_after_end() -> None:
    with pytest.raises(ValidationError):
        WalkForwardSpec.model_validate(_spec_payload(start_date="2026-03-20", end_date="2026-01-05"))


def test_walkforward_spec_rejects_invalid_command() -> None:
    with pytest.raises(ValidationError):
        WalkForwardSpec.model_validate(_spec_payload(command="run-pipeline"))


def test_walkforward_spec_requires_sweep_spec_for_run_sweep() -> None:
    with pytest.raises(ValidationError):
        WalkForwardSpec.model_validate(_spec_payload(command="run-sweep", sweep_spec=None))


def test_walkforward_result_serializes() -> None:
    now = datetime.now()
    result = WalkForwardResult(
        walkforward_id="wf_1",
        name="wf",
        command="run-backtest",
        generated_at=now,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        fold_count=1,
        success_count=1,
        failed_count=0,
        skipped_count=0,
        folds=[
            WalkForwardFold(
                fold_index=1,
                test_start=date(2026, 1, 5),
                test_end=date(2026, 1, 25),
                status="SUCCESS",
                metrics={"total_return": 0.1},
            )
        ],
        stability_metrics={"mean_total_return": 0.1},
        overfit_warnings=[],
        summary="ok",
    )

    assert result.model_dump(mode="json")["folds"][0]["metrics"]["total_return"] == 0.1


def _spec_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "wf",
        "command": "run-backtest",
        "data_dir": "data/sample/ashare_alpha",
        "base_config_dir": "configs/ashare_alpha",
        "output_root_dir": "outputs/walkforward",
        "experiment_registry_dir": "outputs/experiments",
        "start_date": "2026-01-05",
        "end_date": "2026-03-20",
        "test_window_days": 21,
        "step_days": 14,
        "min_test_trading_days": 5,
    }
    payload.update(overrides)
    return payload
