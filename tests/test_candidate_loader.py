from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.candidates import (
    load_candidate_from_experiment,
    load_candidates_from_sweep,
    load_candidates_from_walkforward,
)


def test_load_candidates_from_sweep(tmp_path: Path) -> None:
    path = _write_sweep(tmp_path)

    candidates = load_candidates_from_sweep(path)

    assert len(candidates) == 2
    assert candidates[0].name == "good"
    assert candidates[0].metrics["total_return"] == 0.12
    assert candidates[1].metrics == {}
    assert candidates[1].warnings


def test_load_candidates_from_walkforward(tmp_path: Path) -> None:
    path = _write_walkforward(tmp_path)

    candidates = load_candidates_from_walkforward(path)

    assert len(candidates) == 1
    assert candidates[0].source_type == "walkforward"
    assert candidates[0].metrics["success_fold_count"] == 3
    assert candidates[0].metrics["total_trade_count"] == 5
    assert candidates[0].warnings == ["多数窗口未取得正收益"]


def test_load_candidate_from_experiment(tmp_path: Path) -> None:
    path = _write_experiment(tmp_path, config_dir=str(tmp_path / "config"))

    candidate = load_candidate_from_experiment(path)

    assert candidate.candidate_id == "experiment:exp_20260514_000000_abcd1234"
    assert candidate.metrics["total_return"] == 0.08
    assert candidate.config_dir == str(tmp_path / "config")


def _write_sweep(tmp_path: Path) -> Path:
    payload = {
        "sweep_id": "sweep_1",
        "sweep_name": "sample",
        "command": "run-backtest",
        "generated_at": "2026-05-14T12:00:00",
        "base_config_dir": "configs/ashare_alpha",
        "output_dir": str(tmp_path),
        "registry_dir": str(tmp_path / "experiments"),
        "total_variants": 2,
        "success_count": 1,
        "partial_count": 0,
        "failed_count": 1,
        "runs": [
            {
                "variant_name": "good",
                "status": "SUCCESS",
                "experiment_id": "exp_good",
                "config_dir": str(tmp_path / "good_config"),
                "output_dir": str(tmp_path / "good_output"),
                "metrics": {"total_return": 0.12},
                "error_message": None,
                "started_at": "2026-05-14T12:00:00",
                "finished_at": "2026-05-14T12:00:01",
                "duration_seconds": 1.0,
            },
            {
                "variant_name": "bad",
                "status": "FAILED",
                "experiment_id": None,
                "config_dir": str(tmp_path / "bad_config"),
                "output_dir": str(tmp_path / "bad_output"),
                "metrics": {"total_return": 0.12},
                "error_message": "failed",
                "started_at": "2026-05-14T12:00:00",
                "finished_at": "2026-05-14T12:00:01",
                "duration_seconds": 1.0,
            },
        ],
        "summary": "done",
    }
    path = tmp_path / "sweep_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_walkforward(tmp_path: Path) -> Path:
    folds = [
        {
            "fold_index": index,
            "train_start": None,
            "train_end": None,
            "test_start": "2026-01-01",
            "test_end": "2026-01-10",
            "status": "SUCCESS",
            "experiment_id": f"exp_fold_{index}",
            "output_dir": str(tmp_path / f"fold_{index}"),
            "metrics": {"trade_count": 1 if index == 1 else 2},
            "error_message": None,
        }
        for index in range(1, 4)
    ]
    payload = {
        "walkforward_id": "wf_1",
        "name": "wf sample",
        "command": "run-backtest",
        "generated_at": "2026-05-14T12:00:00",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "fold_count": 3,
        "success_count": 3,
        "failed_count": 0,
        "skipped_count": 0,
        "folds": folds,
        "stability_metrics": {"success_fold_count": 3, "positive_return_ratio": 0.67},
        "overfit_warnings": ["多数窗口未取得正收益"],
        "summary": "done",
    }
    path = tmp_path / "walkforward_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_experiment(tmp_path: Path, config_dir: str | None = None) -> Path:
    payload = {
        "experiment_id": "exp_20260514_000000_abcd1234",
        "created_at": "2026-05-14T12:00:00",
        "command": "run-backtest",
        "command_args": {},
        "data_dir": None,
        "config_dir": config_dir,
        "output_dir": str(tmp_path / "output"),
        "data_source": None,
        "data_version": None,
        "config_hash": "hash",
        "code_version": None,
        "status": "SUCCESS",
        "metrics": [{"name": "total_return", "value": 0.08, "category": "backtest"}],
        "artifacts": [],
        "notes": None,
        "tags": ["tag1"],
    }
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path
