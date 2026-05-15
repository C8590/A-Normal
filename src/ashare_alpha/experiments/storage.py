from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.experiments.models import ExperimentCompareResult, ExperimentIndex, ExperimentRecord


def save_experiment_record(record: ExperimentRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_experiment_record(path: Path) -> ExperimentRecord:
    return ExperimentRecord.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_experiment_index(index: ExperimentIndex, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_experiment_index(path: Path) -> ExperimentIndex:
    return ExperimentIndex.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_compare_result_json(result: ExperimentCompareResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_compare_result_json(path: Path) -> ExperimentCompareResult:
    return ExperimentCompareResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_compare_result_md(result: ExperimentCompareResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_compare_md(result), encoding="utf-8")


def _render_compare_md(result: ExperimentCompareResult) -> str:
    baseline = result.baseline
    target = result.target
    lines = [
        "# 实验对比报告",
        "",
        "## 1. 实验信息",
        f"- baseline: {baseline.experiment_id} ({baseline.command}, {baseline.status})",
        f"- target: {target.experiment_id} ({target.command}, {target.status})",
        "",
        "## 2. 配置和数据版本",
        f"- baseline data_source: {baseline.data_source or '-'}",
        f"- baseline data_version: {baseline.data_version or '-'}",
        f"- baseline config_hash: {baseline.config_hash or '-'}",
        f"- target data_source: {target.data_source or '-'}",
        f"- target data_version: {target.data_version or '-'}",
        f"- target config_hash: {target.config_hash or '-'}",
        "",
        "## 3. 指标差异",
        "| metric | baseline | target | diff | pct_diff |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    if not result.metric_diffs:
        lines.append("| - | - | - | - | - |")
    for metric_name, diff in sorted(result.metric_diffs.items()):
        if isinstance(diff, dict):
            lines.append(
                "| "
                f"{metric_name} | "
                f"{_value(diff.get('baseline_value'))} | "
                f"{_value(diff.get('target_value'))} | "
                f"{_value(diff.get('diff'))} | "
                f"{_pct(diff.get('pct_diff'))} |"
            )
    lines.extend(
        [
            "",
            "## 4. 输出文件",
            f"- baseline output_dir: {baseline.output_dir or '-'}",
            f"- target output_dir: {target.output_dir or '-'}",
            f"- baseline artifacts: {len(baseline.artifacts)}",
            f"- target artifacts: {len(target.artifacts)}",
            "",
            "## 5. 说明",
            f"- {result.summary}",
            "- 仅用于研究对比，不构成投资建议。",
            "- 不保证未来收益。",
            "- 当前系统不自动下单，也未接入券商接口。",
            "",
        ]
    )
    return "\n".join(lines)


def _value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _pct(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{float(value):.2%}"
    return str(value)
