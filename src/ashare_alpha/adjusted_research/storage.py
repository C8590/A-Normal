from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ashare_alpha.adjusted_research.models import AdjustedResearchReport
from ashare_alpha.adjusted_research.renderers import render_adjusted_research_report_md


def save_adjusted_research_report_json(report: AdjustedResearchReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_adjusted_research_report_json(path: Path) -> AdjustedResearchReport:
    return AdjustedResearchReport.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_adjusted_research_report_md(report: AdjustedResearchReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_adjusted_research_report_md(report), encoding="utf-8")


def save_adjusted_research_summary_csv(report: AdjustedResearchReport, path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for comparison in report.factor_comparisons:
        rows.append(
            {
                "section": "factor",
                "left_price_source": comparison.left_price_source,
                "right_price_source": comparison.right_price_source,
                "compared_count": comparison.compared_count,
                "changed_ma20_count": comparison.changed_ma20_count,
                "changed_ma60_count": comparison.changed_ma60_count,
                "max_abs_momentum_20d_diff": comparison.max_abs_momentum_20d_diff,
                "max_abs_momentum_60d_diff": comparison.max_abs_momentum_60d_diff,
                "max_abs_volatility_20d_diff": comparison.max_abs_volatility_20d_diff,
            }
        )
    for comparison in report.backtest_comparisons:
        rows.append(
            {
                "section": "backtest",
                "left_price_source": comparison.left_price_source,
                "right_price_source": comparison.right_price_source,
                "total_return_diff": comparison.total_return_diff,
                "annualized_return_diff": comparison.annualized_return_diff,
                "max_drawdown_diff": comparison.max_drawdown_diff,
                "sharpe_diff": comparison.sharpe_diff,
                "final_equity_diff": comparison.final_equity_diff,
                "trade_count_diff": comparison.trade_count_diff,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames or ["section"]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
