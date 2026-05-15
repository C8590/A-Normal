from __future__ import annotations

from ashare_alpha.realdata.models import RealDataOfflineDrillResult


def render_realdata_offline_drill_report(result: RealDataOfflineDrillResult) -> str:
    pipeline = result.summary.get("pipeline") if isinstance(result.summary.get("pipeline"), dict) else {}
    lines = [
        "# Real Data Offline Drill Report",
        "",
        "## 1. 基本信息",
        f"- drill_id: {result.drill_id}",
        f"- source_name: {result.source_name}",
        f"- data_version: {result.data_version}",
        f"- target_date: {result.target_date.isoformat()}",
        f"- status: {result.status}",
        "",
        "## 2. 步骤状态",
        "| step | status | duration | outputs | error |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for step in result.steps:
        lines.append(
            "| "
            f"{step.name} | "
            f"{step.status} | "
            f"{_duration(step.duration_seconds)} | "
            f"{_outputs(step.output_paths)} | "
            f"{_cell(step.error_message or '-')} |"
        )
    lines.extend(
        [
            "",
            "## 3. 数据目录",
            f"- materialized_data_dir: {result.materialized_data_dir or '-'}",
            f"- imported_data_dir: {result.imported_data_dir or '-'}",
            "",
            "## 4. Pipeline 结果",
            f"- BUY / WATCH / BLOCK: {_value(pipeline.get('buy_count'))} / {_value(pipeline.get('watch_count'))} / {_value(pipeline.get('block_count'))}",
            f"- market_regime: {_value(pipeline.get('market_regime'))}",
            f"- high_risk_count: {_value(pipeline.get('high_risk_count'))}",
            "",
            "## 5. Frontend / Dashboard",
            f"- frontend_output_dir: {result.frontend_output_dir or '-'}",
            f"- dashboard_output_dir: {result.dashboard_output_dir or '-'}",
            "",
            "## 6. Experiment",
            f"- experiment_id: {result.experiment_id or '-'}",
            "",
            "## 7. 安全边界",
            "- 本流程不联网。",
            "- 本流程不接券商接口。",
            "- 本流程不会自动下单。",
            "- 本流程不构成投资建议。",
            "- 本流程不保证收益。",
            "",
        ]
    )
    return "\n".join(lines)


def _duration(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}s"


def _outputs(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(_cell(path) for path in paths)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _value(value: object) -> object:
    return "-" if value is None else value
