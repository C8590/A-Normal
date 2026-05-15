from __future__ import annotations

import json
from pathlib import Path


def write_dashboard_fixture(root: Path) -> dict[str, Path]:
    outputs = root / "outputs"
    paths = {
        "outputs": outputs,
        "pipeline": outputs / "pipelines" / "pipeline_2026-03-20" / "manifest.json",
        "backtest": outputs / "backtests" / "bt_1" / "metrics.json",
        "sweep": outputs / "sweeps" / "sweep_1" / "sweep_result.json",
        "walkforward": outputs / "walkforward" / "wf_1" / "walkforward_result.json",
        "experiment": outputs / "experiments" / "records" / "exp_20260514_000000_abcd1234.json",
        "candidate": outputs / "candidates" / "selection_1" / "candidate_selection.json",
        "quality": outputs / "quality" / "quality_1" / "quality_report.json",
        "audit": outputs / "audit" / "audit_1" / "audit_report.json",
        "security": outputs / "security" / "security_1" / "security_scan_report.json",
        "model": outputs / "models" / "model_1" / "model.json",
        "model_metrics": outputs / "models" / "model_1" / "metrics.json",
        "broken": outputs / "sweeps" / "broken" / "sweep_result.json",
    }
    _write(paths["pipeline"], {"pipeline_date": "2026-03-20", "status": "PARTIAL", "buy_count": 1, "watch_count": 2, "block_count": 3, "high_risk_count": 1, "market_regime": "neutral", "probability_predictable_count": 4})
    _write(paths["backtest"], {"start_date": "2026-01-01", "end_date": "2026-03-20", "final_equity": 10100, "total_return": 0.01, "max_drawdown": -0.02, "sharpe": 0.5, "trade_count": 3, "filled_trade_count": 2, "rejected_trade_count": 1})
    _write(paths["sweep"], {"sweep_id": "sweep_1", "sweep_name": "sweep", "command": "run-backtest", "generated_at": "2026-05-14T12:00:00", "total_variants": 2, "success_count": 1, "failed_count": 1})
    _write(paths["walkforward"], {"walkforward_id": "wf_1", "name": "wf", "command": "run-backtest", "generated_at": "2026-05-14T13:00:00", "fold_count": 3, "success_count": 3, "failed_count": 0, "stability_metrics": {"positive_return_ratio": 0.67}, "overfit_warnings": ["多数窗口未取得正收益"]})
    _write(paths["experiment"], {"experiment_id": "exp_20260514_000000_abcd1234", "created_at": "2026-05-14T14:00:00", "command": "run-backtest", "status": "SUCCESS", "data_source": "local_csv", "data_version": "sample", "metrics": [{"name": "total_return", "value": 0.1}], "tags": ["demo"]})
    _write(paths["candidate"], {"selection_id": "selection_1", "generated_at": "2026-05-14T15:00:00", "total_candidates": 2, "advance_count": 1, "review_count": 1, "reject_count": 0, "scores": [{"candidate_id": "c1", "name": "candidate 1", "total_score": 80, "recommendation": "ADVANCE", "filter_reasons": []}, {"candidate_id": "c2", "name": "candidate 2", "total_score": 60, "recommendation": "REVIEW", "filter_reasons": ["需要复核"]}]})
    _write(paths["quality"], {"generated_at": "2026-05-14T12:00:00", "passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0})
    _write(paths["audit"], {"generated_at": "2026-05-14T12:00:00", "passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0})
    _write(paths["security"], {"generated_at": "2026-05-14T12:00:00", "passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0})
    _write(paths["model"], {"created_at": "2026-05-14T12:00:00", "horizons": [5]})
    _write(paths["model_metrics"], [{"horizon": 5, "accuracy": 0.5}])
    paths["broken"].parent.mkdir(parents=True, exist_ok=True)
    paths["broken"].write_text("{broken", encoding="utf-8")
    return paths


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
