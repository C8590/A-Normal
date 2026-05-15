from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from ashare_alpha.sweeps import SweepRunner


def test_sample_pipeline_thresholds_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", _subprocess_forbidden)
    spec_path = _write_spec(
        tmp_path,
        {
            "sweep_name": "pipeline_smoke",
            "command": "run-pipeline",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": str(tmp_path / "sweeps"),
            "experiment_registry_dir": str(tmp_path / "experiments"),
            "common_args": {"date": "2026-03-20"},
            "variants": [
                {"name": "buy_80", "config_overrides": {"scoring.yaml": {"thresholds.buy": 80}}},
                {"name": "buy_85", "config_overrides": {"scoring.yaml": {"thresholds.buy": 85}}},
            ],
        },
    )

    result = SweepRunner(spec_path).run()

    assert result.success_count == 2
    assert all(Path(run.config_dir).exists() for run in result.runs)
    assert all(Path(run.output_dir).exists() for run in result.runs)
    assert all(run.experiment_id for run in result.runs)
    assert "buy_count" in result.runs[0].metrics
    assert "watch_count" in result.runs[0].metrics
    assert "block_count" in result.runs[0].metrics


def test_variant_failure_does_not_stop_other_variants(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path,
        {
            "sweep_name": "partial_sweep",
            "command": "run-pipeline",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": str(tmp_path / "sweeps"),
            "experiment_registry_dir": str(tmp_path / "experiments"),
            "common_args": {"date": "2026-03-20"},
            "variants": [
                {"name": "bad", "config_overrides": {"scoring.yaml": {"thresholds.missing": 80}}},
                {"name": "good", "config_overrides": {"scoring.yaml": {"thresholds.buy": 85}}},
            ],
        },
    )

    result = SweepRunner(spec_path).run()

    assert result.failed_count == 1
    assert result.success_count == 1
    assert {run.variant_name: run.status for run in result.runs} == {"bad": "FAILED", "good": "SUCCESS"}


def test_sample_backtest_positions_runs_and_extracts_metrics(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path,
        {
            "sweep_name": "backtest_smoke",
            "command": "run-backtest",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": str(tmp_path / "sweeps"),
            "experiment_registry_dir": str(tmp_path / "experiments"),
            "common_args": {"start": "2026-01-05", "end": "2026-03-20"},
            "variants": [
                {"name": "max_pos_1", "config_overrides": {"backtest.yaml": {"max_positions": 1}}},
                {"name": "max_pos_2", "config_overrides": {"backtest.yaml": {"max_positions": 2}}},
            ],
        },
    )

    result = SweepRunner(spec_path).run()

    assert result.success_count == 2
    assert "total_return" in result.runs[0].metrics
    assert "max_drawdown" in result.runs[0].metrics
    assert "sharpe" in result.runs[0].metrics


def _write_spec(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "sweep.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _subprocess_forbidden(*args, **kwargs):
    raise AssertionError("SweepRunner must not call subprocess")
