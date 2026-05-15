from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.experiments import ExperimentMetric, ExperimentRecord, compare_experiments, save_compare_result_md


def test_compare_numeric_metric_diff() -> None:
    result = compare_experiments(_record("base", [ExperimentMetric(name="total_return", value=0.1)]), _record("target", [ExperimentMetric(name="total_return", value=0.15)]))

    assert result.metric_diffs["total_return"]["diff"] == 0.04999999999999999
    assert result.metric_diffs["total_return"]["pct_diff"] == 0.4999999999999999


def test_compare_baseline_zero_pct_diff_none() -> None:
    result = compare_experiments(_record("base", [ExperimentMetric(name="sharpe", value=0)]), _record("target", [ExperimentMetric(name="sharpe", value=1)]))

    assert result.metric_diffs["sharpe"]["pct_diff"] is None


def test_compare_non_numeric_metric() -> None:
    result = compare_experiments(_record("base", [ExperimentMetric(name="status_text", value="ok")]), _record("target", [ExperimentMetric(name="status_text", value="better")]))

    assert result.metric_diffs["status_text"]["baseline_value"] == "ok"
    assert result.metric_diffs["status_text"]["diff"] is None


def test_compare_markdown_report_can_be_generated(tmp_path: Path) -> None:
    result = compare_experiments(_record("base", [ExperimentMetric(name="x", value=1)]), _record("target", [ExperimentMetric(name="x", value=2)]))
    path = tmp_path / "compare.md"

    save_compare_result_md(result, path)

    assert "实验对比报告" in path.read_text(encoding="utf-8")


def _record(label: str, metrics: list[ExperimentMetric]) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=f"exp_20260101_000000_{label[:8].ljust(8, 'a')}",
        created_at=datetime(2026, 1, 1),
        command="run-backtest",
        command_args={},
        status="SUCCESS",
        metrics=metrics,
    )
