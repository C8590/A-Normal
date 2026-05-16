from __future__ import annotations

from ashare_alpha.adjusted.models import AdjustedBuildSummary
from ashare_alpha.adjusted.validation import AdjustedValidationReport


def render_adjusted_report_markdown(
    summary: AdjustedBuildSummary,
    validation_report: AdjustedValidationReport,
) -> str:
    lines = [
        "# 复权行情生成报告",
        "",
        "## 1. 基本信息",
        f"- adj_type: {summary.adj_type}",
        f"- trade_date: {summary.trade_date.isoformat() if summary.trade_date else '-'}",
        f"- start_date: {summary.start_date.isoformat() if summary.start_date else '-'}",
        f"- end_date: {summary.end_date.isoformat() if summary.end_date else '-'}",
        f"- total_records: {summary.total_records}",
        f"- adjusted_records: {summary.adjusted_records}",
        f"- invalid_records: {summary.invalid_records}",
        "",
        "## 2. 质量摘要",
        f"- missing_factor_count: {summary.missing_factor_count}",
        f"- stale_factor_count: {summary.stale_factor_count}",
        f"- error_count: {validation_report.error_count}",
        f"- warning_count: {validation_report.warning_count}",
        f"- info_count: {validation_report.info_count}",
        "",
        "## 3. 主要问题",
        "| severity | issue_type | ts_code | trade_date | message | recommendation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    issues = sorted(validation_report.issues, key=lambda item: (item.severity, item.ts_code or "", item.trade_date or ""))
    if not issues:
        lines.append("| - | - | - | - | 无 | - |")
    for issue in issues[:100]:
        lines.append(
            "| "
            f"{issue.severity} | "
            f"{issue.issue_type} | "
            f"{issue.ts_code or '-'} | "
            f"{issue.trade_date.isoformat() if issue.trade_date else '-'} | "
            f"{_escape_md(issue.message)} | "
            f"{_escape_md(issue.recommendation)} |"
        )
    if len(issues) > 100:
        lines.append(f"| info | truncated | - | - | Only first 100 of {len(issues)} issues are shown. | See JSON report. |")
    lines.extend(
        [
            "",
            "## 4. 说明",
            "- 本复权层基于输入 adjustment_factor 生成。",
            "- 不代表交易所官方复权。",
            "- 仅用于研究。",
            "- 不构成投资建议。",
            "- 不自动下单。",
            "",
        ]
    )
    return "\n".join(lines)


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
