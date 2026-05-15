from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.data.contracts.converters import ExternalConversionResult
from ashare_alpha.data.contracts.models import ExternalContractValidationReport


def save_contract_report_json(report: ExternalContractValidationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_contract_report_md(report: ExternalContractValidationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_contract_report_md(report), encoding="utf-8")


def save_conversion_result_json(result: ExternalConversionResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _render_contract_report_md(report: ExternalContractValidationReport) -> str:
    lines = [
        "# 外部数据源契约检查报告",
        "",
        "## 1. 数据源",
        f"- source_name: {report.source_name}",
        "",
        "## 2. Fixture 目录",
        f"- fixture_dir: {report.fixture_dir}",
        "",
        "## 3. 检查结果",
        f"- passed: {report.passed}",
        f"- total_issues: {report.total_issues}",
        f"- error / warning / info: {report.error_count} / {report.warning_count} / {report.info_count}",
        f"- summary: {report.summary}",
        "",
        "## 4. 数据集行数",
    ]
    for dataset_name, row_count in sorted(report.row_counts.items()):
        lines.append(f"- {dataset_name}: {row_count}")
    lines.extend(
        [
            "",
            "## 5. 问题列表",
            "| severity | dataset | issue_type | field | message | recommendation |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if not report.issues:
        lines.append("| - | - | - | - | 无 | - |")
    for issue in report.issues:
        lines.append(
            "| "
            f"{issue.severity} | "
            f"{issue.dataset_name} | "
            f"{issue.issue_type} | "
            f"{issue.field_name or '-'} | "
            f"{_escape_md(issue.message)} | "
            f"{_escape_md(issue.recommendation)} |"
        )
    lines.extend(
        [
            "",
            "## 6. 后续建议",
            "- 若存在 error，先修复 fixture 必填字段或 CSV 文件缺失问题。",
            "- optional field 的 info 不阻止转换，但会降低样例覆盖面。",
            "- 转换后继续运行 validate-data、quality-report 和 import-data。",
            "- 本报告仅用于离线 Adapter 契约检查，不联网，不构成投资建议。",
            "",
        ]
    )
    return "\n".join(lines)


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
