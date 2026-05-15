from __future__ import annotations

from ashare_alpha.sweeps.models import SweepResult


_PIPELINE_COLUMNS = (
    "buy_count",
    "watch_count",
    "block_count",
    "high_risk_count",
    "allowed_universe_count",
    "probability_predictable_count",
)
_BACKTEST_COLUMNS = (
    "total_return",
    "max_drawdown",
    "sharpe",
    "trade_count",
    "filled_trade_count",
    "rejected_trade_count",
)
_PROBABILITY_COLUMNS = (
    "auc_5d",
    "brier_score_5d",
    "actual_win_rate_5d",
)


def build_metrics_table(result: SweepResult) -> list[dict[str, object]]:
    metric_columns = _columns_for_command(result.command)
    rows: list[dict[str, object]] = []
    for run in result.runs:
        row: dict[str, object] = {
            "variant_name": run.variant_name,
            "status": run.status,
            "experiment_id": run.experiment_id,
            "output_dir": run.output_dir,
            "duration_seconds": run.duration_seconds,
        }
        for column in metric_columns:
            row[column] = run.metrics.get(column, "")
        rows.append(row)
    return rows


def _columns_for_command(command: str) -> tuple[str, ...]:
    if command == "run-pipeline":
        return _PIPELINE_COLUMNS
    if command == "run-backtest":
        return _BACKTEST_COLUMNS
    if command == "train-probability-model":
        return _PROBABILITY_COLUMNS
    return ()


def metric_columns_for_command(command: str) -> tuple[str, ...]:
    return _columns_for_command(command)
