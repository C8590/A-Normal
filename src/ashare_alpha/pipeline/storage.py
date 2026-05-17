from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.pipeline.models import PipelineManifest


def save_pipeline_manifest(manifest: PipelineManifest, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pipeline_manifest(path: Path) -> PipelineManifest:
    if not path.exists():
        raise ValueError(f"manifest.json not found: {path}")
    return PipelineManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_pipeline_summary_md(manifest: PipelineManifest, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_pipeline_summary_markdown(manifest), encoding="utf-8")


def render_pipeline_summary_markdown(manifest: PipelineManifest) -> str:
    lines = [
        "# 研究流水线摘要",
        "",
        "## 1. 基本信息",
        f"- 日期：{manifest.pipeline_date.isoformat()}",
        f"- 数据目录：{manifest.data_dir}",
        f"- 配置目录：{manifest.config_dir}",
        f"- 输出目录：{manifest.output_dir}",
        f"- 模型目录：{manifest.model_dir or '未提供'}",
        "",
        "## 2. 总体状态",
        f"- {manifest.status}",
        "",
        "## 3. 步骤状态",
        "| 步骤 | 状态 | 耗时 | 输出文件 | 摘要 | 错误 |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for step in manifest.steps:
        lines.append(
            f"| {step.name} | {step.status} | {_duration(step.duration_seconds)} | "
            f"{_join(step.output_paths)} | {_summary(step.summary)} | {step.error_message or '-'} |"
        )
    lines.extend(
        [
            "",
            "## 4. 研究摘要",
            f"- 股票总数：{_value(manifest.total_stocks)}",
            f"- 股票池通过数量：{_value(manifest.allowed_universe_count)}",
            f"- BUY / WATCH / BLOCK：{_value(manifest.buy_count)} / {_value(manifest.watch_count)} / {_value(manifest.block_count)}",
            f"- 高风险数量：{_value(manifest.high_risk_count)}",
            f"- 市场状态：{_value(manifest.market_regime)}",
            f"- 概率可预测数量：{_value(manifest.probability_predictable_count)}",
            "",
            "## 5. 主要输出文件",
        ]
    )
    for label, path in [
        ("manifest", str(Path(manifest.output_dir) / "manifest.json")),
        ("pipeline_summary", str(Path(manifest.output_dir) / "pipeline_summary.md")),
        ("universe", manifest.universe_csv_path),
        ("factor", manifest.factor_csv_path),
        ("event", manifest.event_csv_path),
        ("signal", manifest.signal_csv_path),
        ("probability", manifest.probability_csv_path),
        ("leakage_audit", manifest.leakage_audit_path),
        ("quality_report", manifest.quality_report_path),
        ("security_scan", manifest.security_scan_path),
        ("research_gate", manifest.gate_report_path),
        ("daily_report", manifest.daily_report_path),
    ]:
        if path:
            lines.append(f"- {label}：{path}")
    if manifest.gate_decision:
        lines.extend(["", "## 6. Research Quality Gates", f"- gate_decision: {manifest.gate_decision}"])
    lines.extend(
        [
            "",
            "## 6. 风险提示",
            f"- {manifest.disclaimer}",
            "",
        ]
    )
    return "\n".join(lines)


def _duration(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}s"


def _join(values: list[str]) -> str:
    return "<br>".join(values) if values else "-"


def _summary(summary: dict[str, object]) -> str:
    if not summary:
        return "-"
    return "；".join(f"{key}={value}" for key, value in summary.items())


def _value(value: object) -> object:
    return "-" if value is None else value
