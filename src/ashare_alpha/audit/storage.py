from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.audit.models import DataSnapshot, LeakageAuditReport


def save_leakage_audit_report_json(report: LeakageAuditReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_leakage_audit_report_md(report: LeakageAuditReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_leakage_audit_report_markdown(report), encoding="utf-8")


def save_data_snapshot_json(snapshot: DataSnapshot, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_leakage_audit_report_markdown(report: LeakageAuditReport) -> str:
    scope = report.audit_date.isoformat() if report.audit_date else f"{report.start_date} 至 {report.end_date}"
    lines = [
        "# Point-in-Time 防泄漏审计报告",
        "",
        "## 1. 审计范围",
        f"- 审计日期 / 区间：{scope}",
        f"- 数据目录：{report.data_dir}",
        f"- 配置目录：{report.config_dir}",
        f"- 数据源：{report.source_name or '未提供'}",
        f"- 数据版本：{report.data_version or '未提供'}",
        "",
        "## 2. 审计结果",
        f"- passed：{report.passed}",
        f"- total issues：{report.total_issues}",
        f"- error / warning / info：{report.error_count} / {report.warning_count} / {report.info_count}",
        f"- 摘要：{report.summary}",
        "",
        "## 3. 主要问题",
        "| severity | issue_type | dataset | ts_code | trade_date | data_date | available_at | message | recommendation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if report.issues:
        for issue in report.issues:
            lines.append(
                "| "
                f"{issue.severity} | "
                f"{issue.issue_type} | "
                f"{issue.dataset_name} | "
                f"{issue.ts_code or '-'} | "
                f"{issue.trade_date.isoformat() if issue.trade_date else '-'} | "
                f"{issue.data_date.isoformat() if issue.data_date else '-'} | "
                f"{issue.available_at.isoformat() if issue.available_at else '-'} | "
                f"{_escape_md(issue.message)} | "
                f"{_escape_md(issue.recommendation)} |"
            )
    else:
        lines.append("| info | no_issue | - | - | - | - | - | 未发现审计问题 | 继续保留 point-in-time 检查 |")
    lines.extend(
        [
            "",
            "## 4. 数据可见性规则",
            "- 日线：trade_date 15:30 后可见。",
            "- 财务：publish_date 后可见，不能仅按 report_date 判断。",
            "- 公告：event_time 后可见。",
            "",
            "## 5. 风险提示",
            "- 当前审计不代表数据完全无误。",
            "- 它只检查可见性和常见未来函数风险。",
            "- 当前系统不自动下单，不构成投资建议，未接券商接口。",
            "",
        ]
    )
    return "\n".join(lines)


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
