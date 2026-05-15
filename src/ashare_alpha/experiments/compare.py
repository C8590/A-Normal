from __future__ import annotations

from datetime import datetime
from numbers import Number

from ashare_alpha.experiments.models import ExperimentCompareResult, ExperimentMetric, ExperimentRecord


def compare_experiments(baseline: ExperimentRecord, target: ExperimentRecord) -> ExperimentCompareResult:
    baseline_metrics = {metric.name: metric for metric in baseline.metrics}
    target_metrics = {metric.name: metric for metric in target.metrics}
    metric_diffs: dict[str, object] = {}
    improved: list[str] = []
    declined: list[str] = []
    missing: list[str] = []

    for name in sorted(set(baseline_metrics) | set(target_metrics)):
        base_metric = baseline_metrics.get(name)
        target_metric = target_metrics.get(name)
        base_value = _metric_value(base_metric)
        target_value = _metric_value(target_metric)
        if base_metric is None or target_metric is None:
            missing.append(name)
        diff_payload: dict[str, object] = {
            "baseline_value": base_value,
            "target_value": target_value,
        }
        if _is_number(base_value) and _is_number(target_value):
            diff = float(target_value) - float(base_value)
            pct_diff = diff / float(base_value) if float(base_value) != 0 else None
            diff_payload["diff"] = diff
            diff_payload["pct_diff"] = pct_diff
            if diff > 0:
                improved.append(name)
            elif diff < 0:
                declined.append(name)
        else:
            diff_payload["diff"] = None
            diff_payload["pct_diff"] = None
        metric_diffs[name] = diff_payload

    summary = _summary(improved, declined, missing)
    return ExperimentCompareResult(
        generated_at=datetime.now(),
        baseline_experiment_id=baseline.experiment_id,
        target_experiment_id=target.experiment_id,
        metric_diffs=metric_diffs,
        baseline=baseline,
        target=target,
        summary=summary,
    )


def _metric_value(metric: ExperimentMetric | None) -> object:
    return None if metric is None else metric.value


def _is_number(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _summary(improved: list[str], declined: list[str], missing: list[str]) -> str:
    parts = []
    parts.append(f"数值指标上升：{', '.join(improved) if improved else '无'}。")
    parts.append(f"数值指标下降：{', '.join(declined) if declined else '无'}。")
    parts.append(f"缺失或仅单侧存在的指标：{', '.join(missing) if missing else '无'}。")
    parts.append("本报告只做差异展示，不判断未来表现。")
    return "".join(parts)
