from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.quality.models import DataQualityReport, QualityIssue


def save_quality_report_json(report: DataQualityReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_quality_report_md(report: DataQualityReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_quality_report_markdown(report), encoding="utf-8")


def save_quality_issues_csv(report: DataQualityReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "severity",
                "dataset_name",
                "issue_type",
                "ts_code",
                "trade_date",
                "field_name",
                "message",
                "recommendation",
            ],
        )
        writer.writeheader()
        for issue in report.issues:
            writer.writerow(
                {
                    "severity": issue.severity,
                    "dataset_name": issue.dataset_name,
                    "issue_type": issue.issue_type,
                    "ts_code": issue.ts_code or "",
                    "trade_date": issue.trade_date.isoformat() if issue.trade_date else "",
                    "field_name": issue.field_name or "",
                    "message": issue.message,
                    "recommendation": issue.recommendation,
                }
            )


def render_quality_report_markdown(report: DataQualityReport) -> str:
    lines = [
        "# 数据质量报告",
        "",
        "## 1. 数据概览",
        f"- data_dir：{report.data_dir}",
        f"- source_name：{report.source_name or '未提供'}",
        f"- data_version：{report.data_version or '未提供'}",
        "- row_counts：",
    ]
    for key, value in sorted(report.row_counts.items()):
        lines.append(f"  - {key}: {value}")
    lines.append("- coverage：")
    for key, value in sorted(report.coverage.items()):
        lines.append(f"  - {key}: {value}")
    lines.extend(
        [
            "",
            "## 2. 检查结果",
            f"- passed：{report.passed}",
            f"- total issues：{report.total_issues}",
            f"- error / warning / info：{report.error_count} / {report.warning_count} / {report.info_count}",
            f"- 摘要：{report.summary}",
            "",
            "## 3. 严重问题",
        ]
    )
    _append_issue_table(lines, [issue for issue in report.issues if issue.severity == "error"])
    lines.append("")
    lines.append("## 4. 警告问题")
    _append_issue_table(lines, [issue for issue in report.issues if issue.severity == "warning"])
    lines.append("")
    lines.append("## 5. 提示信息")
    _append_issue_table(lines, [issue for issue in report.issues if issue.severity == "info"])
    lines.extend(
        [
            "",
            "## 6. 建议",
        ]
    )
    for recommendation in sorted({issue.recommendation for issue in report.issues}):
        lines.append(f"- {recommendation}")
    if not report.issues:
        lines.append("- 未发现质量问题，继续保留定期检查。")
    lines.extend(
        [
            "",
            "## 7. 风险提示",
            "- 数据质量报告只是辅助检查。",
            "- 不能保证数据完全正确。",
            "- 当前系统不自动下单，不构成投资建议。",
            "",
        ]
    )
    return "\n".join(lines)


def _append_issue_table(lines: list[str], issues: list[QualityIssue]) -> None:
    lines.append("| dataset | issue_type | ts_code | trade_date | field | message | recommendation |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    if not issues:
        lines.append("| - | - | - | - | - | 无 | - |")
        return
    for issue in issues:
        lines.append(
            "| "
            f"{issue.dataset_name} | "
            f"{issue.issue_type} | "
            f"{issue.ts_code or '-'} | "
            f"{issue.trade_date.isoformat() if issue.trade_date else '-'} | "
            f"{issue.field_name or '-'} | "
            f"{_escape_md(issue.message)} | "
            f"{_escape_md(issue.recommendation)} |"
        )


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
