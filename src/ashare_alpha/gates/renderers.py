from __future__ import annotations

from ashare_alpha.gates.models import ResearchGateIssue, ResearchGateReport


def render_research_gate_report_md(report: ResearchGateReport) -> str:
    lines = [
        "# 研究质量门禁报告",
        "",
        "## 1. 总体结论",
        f"- overall_decision: {report.overall_decision}",
        f"- issue_count: {report.issue_count}",
        f"- blocker_count: {report.blocker_count}",
        f"- warning_count: {report.warning_count}",
        f"- info_count: {report.info_count}",
        "",
        "## 2. 输入产物",
        "| artifact_type | path | status | decision | issue_count |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for summary in report.artifact_summaries:
        lines.append(
            "| "
            f"{_escape(summary.artifact_type)} | "
            f"{_escape(summary.path)} | "
            f"{_escape(summary.status or '-')} | "
            f"{summary.decision} | "
            f"{summary.issue_count} |"
        )
    lines.extend(["", "## 3. BLOCKER 问题"])
    lines.extend(_issue_lines(report.issues, "BLOCKER"))
    lines.extend(["", "## 4. WARNING 问题"])
    lines.extend(_issue_lines(report.issues, "WARNING"))
    lines.extend(["", "## 5. INFO 信息"])
    lines.extend(_issue_lines(report.issues, "INFO"))
    lines.extend(["", "## 6. 建议"])
    if report.overall_decision == "BLOCK":
        lines.append("- 不建议晋级，不建议发布，不建议 promote。")
    elif report.overall_decision == "WARN":
        lines.append("- 需要人工复核。")
    else:
        lines.append("- 可进入下一轮研究，但不代表未来收益。")
    lines.extend(
        [
            "",
            "## 7. 说明",
            "- 仅用于研究质量控制。",
            "- 不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "- 未接券商接口。",
            "",
            report.summary,
            "",
        ]
    )
    return "\n".join(lines)


def _issue_lines(issues: list[ResearchGateIssue], severity: str) -> list[str]:
    rows = [issue for issue in issues if issue.severity == severity]
    if not rows:
        return ["- none"]
    return [
        f"- [{issue.artifact_type}] {issue.issue_type}: {issue.message} 建议：{issue.recommendation} ({issue.artifact_path or '-'})"
        for issue in rows
    ]


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
