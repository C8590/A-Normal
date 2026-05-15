from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from ashare_alpha.backtest.engine import BacktestEngine
from ashare_alpha.walkforward import WalkForwardRunner


def test_sample_backtest_walkforward_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", _subprocess_forbidden)
    spec_path = _write_spec(tmp_path, _base_spec(tmp_path))

    result = WalkForwardRunner(spec_path).run()

    assert result.fold_count >= 2
    assert result.success_count == result.fold_count
    assert all(fold.output_dir and Path(fold.output_dir).exists() for fold in result.folds)
    assert all(fold.experiment_id for fold in result.folds if fold.status == "SUCCESS")
    output_dir = Path(result.folds[0].output_dir).parents[1]
    assert (output_dir / "walkforward_result.json").exists()
    assert (output_dir / "walkforward_summary.md").exists()
    assert (output_dir / "fold_metrics.csv").exists()


def test_single_fold_failure_does_not_stop_other_folds(tmp_path: Path, monkeypatch) -> None:
    original_run = BacktestEngine.run

    def fail_first(self, start_date, end_date):
        if start_date.isoformat() == "2026-01-05":
            raise ValueError("planned fold failure")
        return original_run(self, start_date, end_date)

    monkeypatch.setattr("ashare_alpha.walkforward.runner.BacktestEngine.run", fail_first)
    payload = _base_spec(tmp_path)
    payload["test_window_days"] = 14
    payload["step_days"] = 14
    spec_path = _write_spec(tmp_path, payload)

    result = WalkForwardRunner(spec_path).run()

    assert result.failed_count == 1
    assert result.success_count >= 1


def test_walkforward_skips_short_trading_windows(tmp_path: Path) -> None:
    payload = _base_spec(tmp_path)
    payload["min_test_trading_days"] = 99
    spec_path = _write_spec(tmp_path, payload)

    result = WalkForwardRunner(spec_path).run()

    assert result.skipped_count == result.fold_count
    assert all(fold.status == "SKIPPED" for fold in result.folds)


def test_walkforward_can_run_sweep_folds(tmp_path: Path) -> None:
    sweep_spec_path = tmp_path / "sweep.yaml"
    sweep_spec_path.write_text(
        yaml.safe_dump(
            {
                "sweep_name": "wf_sweep",
                "command": "run-backtest",
                "base_config_dir": "configs/ashare_alpha",
                "data_dir": "data/sample/ashare_alpha",
                "output_root_dir": str(tmp_path / "sweeps"),
                "experiment_registry_dir": str(tmp_path / "experiments"),
                "common_args": {"start": "2026-01-05", "end": "2026-01-20"},
                "variants": [
                    {"name": "max_pos_1", "config_overrides": {"backtest.yaml": {"max_positions": 1}}},
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    payload = _base_spec(tmp_path)
    payload["command"] = "run-sweep"
    payload["sweep_spec"] = str(sweep_spec_path)
    payload["test_window_days"] = 14
    payload["step_days"] = 14
    spec_path = _write_spec(tmp_path, payload)

    result = WalkForwardRunner(spec_path).run()

    assert result.success_count == result.fold_count
    assert "mean_total_return" in result.folds[0].metrics
    assert all(fold.experiment_id for fold in result.folds)


def _base_spec(tmp_path: Path) -> dict[str, object]:
    return {
        "name": "runner_wf",
        "command": "run-backtest",
        "data_dir": "data/sample/ashare_alpha",
        "base_config_dir": "configs/ashare_alpha",
        "output_root_dir": str(tmp_path / "walkforward"),
        "experiment_registry_dir": str(tmp_path / "experiments"),
        "start_date": "2026-01-05",
        "end_date": "2026-03-20",
        "train_window_days": None,
        "test_window_days": 21,
        "step_days": 14,
        "min_test_trading_days": 5,
        "common_args": {},
        "tags": ["test"],
    }


def _write_spec(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "walkforward.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _subprocess_forbidden(*args, **kwargs):
    raise AssertionError("WalkForwardRunner must not call subprocess")
