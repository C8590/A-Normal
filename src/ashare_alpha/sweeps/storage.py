from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.sweeps.metrics_table import metric_columns_for_command
from ashare_alpha.sweeps.models import SweepResult


def save_sweep_result_json(result: SweepResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_sweep_result_json(path: Path) -> SweepResult:
    return SweepResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_sweep_summary_md(result: SweepResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_summary(result), encoding="utf-8")


def save_metrics_table_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _render_summary(result: SweepResult) -> str:
    metric_columns = metric_columns_for_command(result.command)
    header = ["variant", "status", "experiment_id", *metric_columns, "error"]
    lines = [
        "# Sweep 实验摘要",
        "",
        "## 1. 基本信息",
        f"- sweep_id: {result.sweep_id}",
        f"- sweep_name: {result.sweep_name}",
        f"- command: {result.command}",
        f"- total variants: {result.total_variants}",
        f"- success / partial / failed: {result.success_count} / {result.partial_count} / {result.failed_count}",
        "",
        "## 2. Variant 结果",
        _table_row(header),
        _table_row(["---"] * len(header)),
    ]
    for run in result.runs:
        values = [
            run.variant_name,
            run.status,
            run.experiment_id or "-",
            *[_format_value(run.metrics.get(column)) for column in metric_columns],
            run.error_message or "-",
        ]
        lines.append(_table_row(values))

    lines.extend(["", "## 3. 配置变更说明"])
    for run in result.runs:
        lines.append(f"### {run.variant_name}")
        changes = _read_config_changes(run.config_dir)
        if not changes:
            lines.append("- 无配置覆盖")
        else:
            lines.extend(f"- {change}" for change in changes)

    lines.extend(
        [
            "",
            "## 4. 输出文件",
            f"- sweep_result.json: {Path(result.output_dir) / 'sweep_result.json'}",
            f"- metrics_table.csv: {Path(result.output_dir) / 'metrics_table.csv'}",
        ]
    )
    for run in result.runs:
        lines.append(f"- {run.variant_name} output: {run.output_dir}")

    lines.extend(
        [
            "",
            "## 5. 说明",
            "- 仅用于研究比较。",
            "- 不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "",
            result.summary,
            "",
        ]
    )
    return "\n".join(lines)


def _read_config_changes(config_dir: str) -> list[str]:
    path = Path(config_dir).parent / "config_changes.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _table_row(values: list[object]) -> str:
    return "| " + " | ".join(_escape_md(str(value)) for value in values) + " |"


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_value(value: object) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
