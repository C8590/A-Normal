from __future__ import annotations

from typing import Any

from ashare_alpha.dashboard.models import DashboardArtifact, DashboardIndex, DashboardSummary


def render_dashboard_markdown(index: DashboardIndex, summary: DashboardSummary) -> str:
    lines = [
        "# 研究 Dashboard",
        "",
        "## 1. 总览",
        f"- 生成时间: {summary.generated_at.isoformat()}",
        f"- outputs_root: {index.outputs_root}",
        f"- artifact_count: {index.artifact_count}",
        "- 各类型数量:",
    ]
    if index.artifacts_by_type:
        lines.extend(f"  - {key}: {value}" for key, value in sorted(index.artifacts_by_type.items()))
    else:
        lines.append("  - 未发现研究产物")
    lines.extend(["", summary.summary_text, "", "## 2. 最新研究产物"])
    latest_rows = [
        ("pipeline", summary.latest_pipeline),
        ("backtest", summary.latest_backtest),
        ("sweep", summary.latest_sweep),
        ("walkforward", summary.latest_walkforward),
        ("candidate_selection", summary.latest_candidate_selection),
    ]
    lines.extend(["| 类型 | 名称 | 状态 | 路径 | 关键摘要 |", "| --- | --- | --- | --- | --- |"])
    for label, artifact in latest_rows:
        lines.append(_artifact_table_row(label, artifact))
    lines.extend(["", "## 3. 最新 Pipeline", *_detail_lines(summary.latest_pipeline, ("buy_count", "watch_count", "block_count", "market_regime", "high_risk_count"))])
    lines.extend(["", "## 4. 最新 Backtest", *_detail_lines(summary.latest_backtest, ("total_return", "max_drawdown", "sharpe", "trade_count"))])
    lines.extend(["", "## 5. 最新 Sweep", *_detail_lines(summary.latest_sweep, ("total_variants", "success_count", "failed_count"))])
    lines.extend(
        [
            "",
            "## 6. 最新 Walk-forward",
            *_detail_lines(summary.latest_walkforward, ("fold_count", "success_count")),
        ]
    )
    if summary.latest_walkforward:
        stability = summary.latest_walkforward.summary.get("stability_metrics", {})
        if isinstance(stability, dict):
            lines.append(f"- positive_return_ratio: {_value(stability.get('positive_return_ratio'))}")
        warnings = summary.latest_walkforward.summary.get("overfit_warnings", [])
        lines.append(f"- overfit_warnings: {_value(warnings)}")
    lines.extend(["", "## 7. 候选配置"])
    if summary.top_candidates:
        lines.extend(["| rank | candidate_id | name | total_score | recommendation | filter_reasons |", "| ---: | --- | --- | ---: | --- | --- |"])
        for rank, candidate in enumerate(summary.top_candidates, start=1):
            lines.append(
                "| "
                f"{rank} | "
                f"{_escape(_value(candidate.get('candidate_id')))} | "
                f"{_escape(_value(candidate.get('name')))} | "
                f"{_escape(_value(candidate.get('total_score')))} | "
                f"{_escape(_value(candidate.get('recommendation')))} | "
                f"{_escape(_value(candidate.get('filter_reasons')))} |"
            )
    else:
        lines.append("- 未发现候选配置评估结果。")
    lines.extend(["", "## 8. 最近实验"])
    if summary.recent_experiments:
        lines.extend(["| experiment_id | command | status | data | tags |", "| --- | --- | --- | --- | --- |"])
        for experiment in summary.recent_experiments:
            data = f"{experiment.get('data_source') or '-'}/{experiment.get('data_version') or '-'}"
            lines.append(
                "| "
                f"{_escape(_value(experiment.get('experiment_id')))} | "
                f"{_escape(_value(experiment.get('command')))} | "
                f"{_escape(_value(experiment.get('status')))} | "
                f"{_escape(data)} | "
                f"{_escape(_value(experiment.get('tags')))} |"
            )
    else:
        lines.append("- 未发现实验记录。")
    lines.extend(["", "## 9. 风险与告警"])
    if summary.warning_items:
        for item in summary.warning_items:
            lines.append(f"- [{item.get('artifact_type')}] {item.get('name')}: {item.get('message')} ({item.get('path')})")
    else:
        lines.append("- 当前汇总未发现需要优先处理的告警。")
    lines.extend(
        [
            "",
            "## 10. 说明",
            "- 本 Dashboard 只汇总研究产物。",
            "- 不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "",
        ]
    )
    return "\n".join(lines)


def dashboard_to_json_dict(index: DashboardIndex, summary: DashboardSummary) -> dict[str, Any]:
    return {
        "index": index.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
    }


def _artifact_table_row(label: str, artifact: DashboardArtifact | None) -> str:
    if artifact is None:
        return f"| {label} | - | - | - | - |"
    return (
        "| "
        f"{label} | "
        f"{_escape(artifact.name)} | "
        f"{_escape(artifact.status or '-')} | "
        f"{_escape(artifact.path)} | "
        f"{_escape(_value(artifact.summary))} |"
    )


def _detail_lines(artifact: DashboardArtifact | None, keys: tuple[str, ...]) -> list[str]:
    if artifact is None:
        return ["- 未发现。"]
    lines = [f"- name: {artifact.name}", f"- status: {artifact.status or '-'}", f"- path: {artifact.path}"]
    for key in keys:
        lines.append(f"- {key}: {_value(artifact.summary.get(key))}")
    return lines


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, list):
        if not value:
            return "-"
        return "；".join(_value(item) for item in value)
    if isinstance(value, dict):
        if not value:
            return "-"
        return "；".join(f"{key}={_value(item)}" for key, item in value.items())
    return str(value)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
