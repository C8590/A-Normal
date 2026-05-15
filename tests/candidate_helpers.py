from __future__ import annotations

import json
from pathlib import Path

import yaml

from ashare_alpha.candidates import CandidateRules


def candidate_rules() -> CandidateRules:
    return CandidateRules.model_validate(candidate_rules_payload())


def write_candidate_rules(tmp_path: Path) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump(candidate_rules_payload(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def candidate_rules_payload() -> dict[str, object]:
    return {
        "selection_name": "test_rules",
        "weights": {
            "return_score": 0.25,
            "drawdown_score": 0.25,
            "stability_score": 0.25,
            "trade_activity_score": 0.10,
            "warning_penalty_score": 0.15,
        },
        "thresholds": {
            "min_success_fold_count": 3,
            "min_positive_return_ratio": 0.5,
            "max_allowed_worst_drawdown": -0.15,
            "min_trade_count_total": 0,
            "max_warning_count": 5,
        },
        "scoring": {"return_cap": 0.20, "drawdown_floor": -0.20, "stability_std_cap": 0.10},
        "promotion": {
            "allow_auto_promote": False,
            "promoted_config_root": "outputs/candidate_configs",
            "require_manual_flag": True,
        },
    }


def write_wf_source(
    tmp_path: Path,
    name: str,
    mean_return: float,
    worst_drawdown: float,
    positive_ratio: float,
    std_return: float,
    success_count: int,
    trade_count: int,
) -> Path:
    payload = {
        "walkforward_id": name,
        "name": name,
        "command": "run-backtest",
        "generated_at": "2026-05-14T12:00:00",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "fold_count": success_count,
        "success_count": success_count,
        "failed_count": 0,
        "skipped_count": 0,
        "folds": [
            {
                "fold_index": index,
                "train_start": None,
                "train_end": None,
                "test_start": "2026-01-01",
                "test_end": "2026-01-10",
                "status": "SUCCESS",
                "experiment_id": None,
                "output_dir": None,
                "metrics": {"trade_count": trade_count if index == 1 else 0},
                "error_message": None,
            }
            for index in range(1, success_count + 1)
        ],
        "stability_metrics": {
            "success_fold_count": success_count,
            "positive_return_ratio": positive_ratio,
            "mean_total_return": mean_return,
            "std_total_return": std_return,
            "worst_max_drawdown": worst_drawdown,
        },
        "overfit_warnings": [],
        "summary": "done",
    }
    path = tmp_path / f"{name}_walkforward_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def write_sweep_source(tmp_path: Path) -> Path:
    payload = {
        "sweep_id": "sweep_selector",
        "sweep_name": "selector",
        "command": "run-backtest",
        "generated_at": "2026-05-14T12:00:00",
        "base_config_dir": "configs/ashare_alpha",
        "output_dir": str(tmp_path),
        "registry_dir": str(tmp_path / "experiments"),
        "total_variants": 2,
        "success_count": 2,
        "partial_count": 0,
        "failed_count": 0,
        "runs": [
            sweep_run(tmp_path, "review", 0.15, -0.05, 1),
            sweep_run(tmp_path, "reject", -0.1, -0.18, 0),
        ],
        "summary": "done",
    }
    path = tmp_path / "sweep_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def sweep_run(tmp_path: Path, name: str, total_return: float, max_drawdown: float, trade_count: int) -> dict[str, object]:
    return {
        "variant_name": name,
        "status": "SUCCESS",
        "experiment_id": f"exp_{name}",
        "config_dir": str(tmp_path / f"{name}_config"),
        "output_dir": str(tmp_path / f"{name}_output"),
        "metrics": {"total_return": total_return, "max_drawdown": max_drawdown, "trade_count": trade_count},
        "error_message": None,
        "started_at": "2026-05-14T12:00:00",
        "finished_at": "2026-05-14T12:00:01",
        "duration_seconds": 1.0,
    }
