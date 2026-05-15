from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from ashare_alpha.walkforward.models import WalkForwardFold, WalkForwardResult
from ashare_alpha.walkforward.storage import (
    load_walkforward_result_json,
    save_fold_metrics_csv,
    save_walkforward_result_json,
    save_walkforward_summary_md,
)


def test_walkforward_result_json_round_trips(tmp_path: Path) -> None:
    result = _result()
    path = tmp_path / "walkforward_result.json"

    save_walkforward_result_json(result, path)

    assert load_walkforward_result_json(path).walkforward_id == "wf_1"


def test_walkforward_summary_md_saves(tmp_path: Path) -> None:
    path = tmp_path / "walkforward_summary.md"

    save_walkforward_summary_md(_result(), path)

    assert "# Walk-forward 样本外验证报告" in path.read_text(encoding="utf-8")


def test_fold_metrics_csv_saves(tmp_path: Path) -> None:
    path = tmp_path / "fold_metrics.csv"

    save_fold_metrics_csv(_result(), path)

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["fold_index"] == "1"
    assert rows[0]["total_return"] == "0.1"


def _result() -> WalkForwardResult:
    return WalkForwardResult(
        walkforward_id="wf_1",
        name="wf",
        command="run-backtest",
        generated_at=datetime.now(),
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
                experiment_id="exp_1",
                output_dir="output",
                metrics={"total_return": 0.1, "max_drawdown": -0.02, "sharpe": 1.0, "trade_count": 1},
            )
        ],
        stability_metrics={"mean_total_return": 0.1},
        overfit_warnings=[],
        summary="ok",
    )
