from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.security.models import SecurityScanReport


def save_security_scan_report_json(report: SecurityScanReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def save_security_scan_report_md(report: SecurityScanReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_security_scan_report_md(report), encoding="utf-8")


def _render_security_scan_report_md(report: SecurityScanReport) -> str:
    lines = [
        "# 安全配置扫描报告",
        "",
        "## 1. 扫描范围",
        f"- config_dir: {report.config_dir}",
        "",
        "## 2. 结果摘要",
        f"- passed: {report.passed}",
        f"- total_issues: {report.total_issues}",
        f"- error / warning / info: {report.error_count} / {report.warning_count} / {report.info_count}",
        f"- summary: {report.summary}",
        "",
        "## 3. 问题列表",
        "| severity | file | key_path | issue_type | message | recommendation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not report.issues:
        lines.append("| - | - | - | - | 无 | - |")
    for issue in report.issues:
        lines.append(
            "| "
            f"{issue.severity} | "
            f"{issue.file_path} | "
            f"{issue.key_path or '-'} | "
            f"{issue.issue_type} | "
            f"{_escape_md(issue.message)} | "
            f"{_escape_md(issue.recommendation)} |"
        )
    lines.extend(
        [
            "",
            "## 4. 安全建议",
            "- 不要把 API key、token 或 password 写进配置文件。",
            "- 使用环境变量传递密钥，并只在配置里写环境变量名。",
            "- 默认保持 offline_mode=true，除非有明确审批，不允许联网。",
            "- 当前系统不自动下单，不接券商接口，不构成投资建议。",
            "",
        ]
    )
    return "\n".join(lines)


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
