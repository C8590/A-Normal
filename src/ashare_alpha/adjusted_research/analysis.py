from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ashare_alpha.adjusted_research.models import (
    AdjustedBacktestComparisonSummary,
    AdjustedFactorComparisonSummary,
    AdjustedResearchReport,
)


def summarize_factor_comparison(compare_csv_path: Path) -> AdjustedFactorComparisonSummary:
    rows = _read_csv_dicts(compare_csv_path)
    left = _first_non_empty(rows, "left_price_source") or "raw"
    right = _first_non_empty(rows, "right_price_source") or "qfq"
    top_rows = sorted(rows, key=_row_max_abs_diff, reverse=True)[:10]
    return AdjustedFactorComparisonSummary(
        left_price_source=left,
        right_price_source=right,
        compared_count=len(rows),
        changed_ma20_count=sum(1 for row in rows if _bool_cell(row.get("close_above_ma20_changed"))),
        changed_ma60_count=sum(1 for row in rows if _bool_cell(row.get("close_above_ma60_changed"))),
        max_abs_momentum_20d_diff=_max_abs(rows, "momentum_20d_diff"),
        max_abs_momentum_60d_diff=_max_abs(rows, "momentum_60d_diff"),
        max_abs_volatility_20d_diff=_max_abs(rows, "volatility_20d_diff"),
        top_differences=[_top_difference_row(row) for row in top_rows],
    )


def summarize_backtest_comparison(compare_json_path: Path) -> AdjustedBacktestComparisonSummary:
    payload = json.loads(Path(compare_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"backtest comparison must be a JSON object: {compare_json_path}")
    diff = payload.get("diff")
    if not isinstance(diff, dict):
        diff = {}
    left = str(payload.get("left") or "raw")
    right = str(payload.get("right") or "qfq")
    return AdjustedBacktestComparisonSummary(
        left_price_source=left,
        right_price_source=right,
        total_return_diff=_float_or_none(diff.get("total_return_diff")),
        annualized_return_diff=_float_or_none(diff.get("annualized_return_diff")),
        max_drawdown_diff=_float_or_none(diff.get("max_drawdown_diff")),
        sharpe_diff=_float_or_none(diff.get("sharpe_diff")),
        final_equity_diff=_float_or_none(diff.get("final_equity_diff")),
        trade_count_diff=_int_or_none(diff.get("trade_count_diff")),
        summary={
            "execution_price_source": payload.get("execution_price_source"),
            "left_adjusted_valuation_warning_count": payload.get("left_adjusted_valuation_warning_count"),
            "right_adjusted_valuation_warning_count": payload.get("right_adjusted_valuation_warning_count"),
            "left_metrics": payload.get("left_metrics", {}),
            "right_metrics": payload.get("right_metrics", {}),
        },
    )


def build_adjusted_research_warnings(report: AdjustedResearchReport) -> list[str]:
    warnings: list[str] = []
    factor_steps = {
        str(step.summary.get("price_source")): step
        for step in report.steps
        if step.name.startswith("compute-factors ") and step.status == "SUCCESS"
    }
    raw_factor = factor_steps.get("raw")
    raw_computable = _summary_int(raw_factor, "computable")
    for source in ("qfq", "hfq"):
        step = factor_steps.get(source)
        computable = _summary_int(step, "computable")
        if raw_computable is not None and computable is not None and computable < raw_computable:
            warnings.append(
                f"WARNING: {source} factor computable count {computable} is lower than raw {raw_computable}; review adjusted data coverage."
            )
        issue_count = _summary_int(step, "adjusted_issue_count")
        if issue_count and issue_count > 0:
            warnings.append(f"WARNING: {source} factors include {issue_count} adjusted data quality issue rows.")

    for comparison in report.backtest_comparisons:
        source = comparison.right_price_source
        if comparison.total_return_diff is not None and abs(comparison.total_return_diff) >= 0.05:
            warnings.append(
                f"WARNING: raw vs {source} total_return_diff is {comparison.total_return_diff:.6f}; treat this as research-basis sensitivity."
            )
        if comparison.sharpe_diff is not None and abs(comparison.sharpe_diff) >= 1.0:
            warnings.append(
                f"WARNING: raw vs {source} sharpe_diff is {comparison.sharpe_diff:.6f}; review valuation-basis sensitivity."
            )
        right_warning_count = _int_or_none(comparison.summary.get("right_adjusted_valuation_warning_count"))
        if right_warning_count and right_warning_count > 0:
            warnings.append(f"WARNING: {source} backtest used raw valuation fallback {right_warning_count} times.")

    backtest_steps = [
        step
        for step in report.steps
        if step.name.startswith("run-backtest ") and step.status == "SUCCESS"
    ]
    if backtest_steps and all(_summary_int(step, "trade_count") == 0 for step in backtest_steps):
        warnings.append("INFO: 当前样例无交易或阈值严格，回测无法验证交易收益差异。")
    return warnings


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _first_non_empty(rows: list[dict[str, str]], key: str) -> str | None:
    for row in rows:
        value = row.get(key)
        if value:
            return value
    return None


def _max_abs(rows: list[dict[str, str]], key: str) -> float | None:
    values = [abs(value) for row in rows if (value := _float_or_none(row.get(key))) is not None]
    return max(values) if values else None


def _row_max_abs_diff(row: dict[str, str]) -> float:
    fields = (
        "momentum_5d_diff",
        "momentum_20d_diff",
        "momentum_60d_diff",
        "ma20_diff",
        "ma60_diff",
        "volatility_20d_diff",
        "max_drawdown_20d_diff",
    )
    values = [abs(value) for field in fields if (value := _float_or_none(row.get(field))) is not None]
    return max(values) if values else 0.0


def _top_difference_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "ts_code": row.get("ts_code"),
        "max_abs_diff": _row_max_abs_diff(row),
        "ma20_diff": _float_or_none(row.get("ma20_diff")),
        "ma60_diff": _float_or_none(row.get("ma60_diff")),
        "momentum_20d_diff": _float_or_none(row.get("momentum_20d_diff")),
        "momentum_60d_diff": _float_or_none(row.get("momentum_60d_diff")),
        "volatility_20d_diff": _float_or_none(row.get("volatility_20d_diff")),
        "left_missing_reasons": row.get("left_missing_reasons") or "",
        "right_missing_reasons": row.get("right_missing_reasons") or "",
    }


def _summary_int(step: object | None, key: str) -> int | None:
    if step is None or not hasattr(step, "summary"):
        return None
    summary = getattr(step, "summary")
    if not isinstance(summary, dict):
        return None
    return _int_or_none(summary.get(key))


def _bool_cell(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def _float_or_none(value: object) -> float | None:
    if value in {None, ""} or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: object) -> int | None:
    if value in {None, ""} or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
