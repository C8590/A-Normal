from __future__ import annotations

from typing import Any

from ashare_alpha.adjusted_research.models import (
    AdjustedBacktestComparisonSummary,
    AdjustedFactorComparisonSummary,
    AdjustedResearchReport,
)


def render_adjusted_research_report_md(report: AdjustedResearchReport) -> str:
    lines = [
        "# 复权研究对比报告",
        "",
        "## 1. 基本信息",
        f"- report_id: {report.report_id}",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- target_date: {report.target_date.isoformat()}",
        f"- start_date: {report.start_date.isoformat()}",
        f"- end_date: {report.end_date.isoformat()}",
        f"- data_dir: {report.data_dir}",
        f"- config_dir: {report.config_dir}",
        f"- status: {report.status}",
        f"- output_dir: {report.output_dir}",
        "",
        "## 2. 步骤状态",
        "| step | status | duration | outputs | error |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for step in report.steps:
        lines.append(
            "| "
            f"{_escape(step.name)} | "
            f"{step.status} | "
            f"{_format_optional_float(step.duration_seconds)} | "
            f"{_escape('; '.join(step.output_paths))} | "
            f"{_escape(step.error_message or '')} |"
        )
    lines.extend(["", "## 3. 因子差异：raw vs qfq"])
    lines.extend(_factor_section(_find_factor(report.factor_comparisons, "qfq")))
    lines.extend(["", "## 4. 因子差异：raw vs hfq"])
    lines.extend(_factor_section(_find_factor(report.factor_comparisons, "hfq")))
    lines.extend(["", "## 5. 回测差异：raw vs qfq"])
    lines.extend(_backtest_section(_find_backtest(report.backtest_comparisons, "qfq")))
    lines.extend(["", "## 6. 回测差异：raw vs hfq"])
    lines.extend(_backtest_section(_find_backtest(report.backtest_comparisons, "hfq")))
    lines.extend(["", "## 7. 风险与解释"])
    if report.warning_items:
        lines.extend(f"- {item}" for item in report.warning_items)
    else:
        lines.append("- 未发现需要优先复核的复权研究提示。")
    lines.extend(
        [
            "",
            "## 8. 重要说明",
            "- qfq/hfq 只是研究估值口径。",
            "- 真实成交约束仍基于 raw。",
            "- adjusted price 不代表真实成交价。",
            "- 本报告不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "- 未接券商接口。",
            "",
        ]
    )
    return "\n".join(lines)


def _factor_section(summary: AdjustedFactorComparisonSummary | None) -> list[str]:
    if summary is None:
        return ["- 未生成该因子对比。"]
    lines = [
        f"- compared_count: {summary.compared_count}",
        f"- changed_ma20_count: {summary.changed_ma20_count}",
        f"- changed_ma60_count: {summary.changed_ma60_count}",
        f"- max_abs_momentum_20d_diff: {_format_optional_float(summary.max_abs_momentum_20d_diff)}",
        f"- max_abs_momentum_60d_diff: {_format_optional_float(summary.max_abs_momentum_60d_diff)}",
        f"- max_abs_volatility_20d_diff: {_format_optional_float(summary.max_abs_volatility_20d_diff)}",
        "",
        "| ts_code | max_abs_diff | ma20_diff | ma60_diff | momentum_20d_diff | volatility_20d_diff |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.top_differences[:10]:
        lines.append(
            "| "
            f"{_escape(_value(row.get('ts_code')))} | "
            f"{_format_optional_float(row.get('max_abs_diff'))} | "
            f"{_format_optional_float(row.get('ma20_diff'))} | "
            f"{_format_optional_float(row.get('ma60_diff'))} | "
            f"{_format_optional_float(row.get('momentum_20d_diff'))} | "
            f"{_format_optional_float(row.get('volatility_20d_diff'))} |"
        )
    return lines


def _backtest_section(summary: AdjustedBacktestComparisonSummary | None) -> list[str]:
    if summary is None:
        return ["- 未生成该回测对比。"]
    return [
        f"- total_return_diff: {_format_optional_float(summary.total_return_diff)}",
        f"- annualized_return_diff: {_format_optional_float(summary.annualized_return_diff)}",
        f"- max_drawdown_diff: {_format_optional_float(summary.max_drawdown_diff)}",
        f"- sharpe_diff: {_format_optional_float(summary.sharpe_diff)}",
        f"- final_equity_diff: {_format_optional_float(summary.final_equity_diff)}",
        f"- trade_count_diff: {_value(summary.trade_count_diff)}",
    ]


def _find_factor(
    summaries: list[AdjustedFactorComparisonSummary],
    right_source: str,
) -> AdjustedFactorComparisonSummary | None:
    return next((item for item in summaries if item.left_price_source == "raw" and item.right_price_source == right_source), None)


def _find_backtest(
    summaries: list[AdjustedBacktestComparisonSummary],
    right_source: str,
) -> AdjustedBacktestComparisonSummary | None:
    return next((item for item in summaries if item.left_price_source == "raw" and item.right_price_source == right_source), None)


def _format_optional_float(value: object) -> str:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return "-"
    return f"{value:.8g}"


def _value(value: Any) -> str:
    return "-" if value is None else str(value)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
