from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from ashare_alpha.adjusted import (
    AdjustedDailyBarBuilder,
    save_adjusted_daily_bar_csv,
    save_adjusted_report_md,
    save_adjusted_summary_json,
    save_adjusted_validation_json,
    validate_adjusted_records,
)
from ashare_alpha.adjusted_research.analysis import (
    build_adjusted_research_warnings,
    summarize_backtest_comparison,
    summarize_factor_comparison,
)
from ashare_alpha.adjusted_research.models import (
    AdjustedBacktestComparisonSummary,
    AdjustedFactorComparisonSummary,
    AdjustedResearchReport,
    AdjustedResearchStepResult,
)
from ashare_alpha.adjusted_research.storage import (
    save_adjusted_research_report_json,
    save_adjusted_research_report_md,
    save_adjusted_research_summary_csv,
)
from ashare_alpha.backtest import (
    BacktestEngine,
    BacktestResult,
    save_backtest_summary_md,
    save_daily_equity_csv,
    save_metrics_json,
    save_trades_csv,
)
from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.realism import OptionalRealismDataLoader
from ashare_alpha.factors import FactorBuilder, save_factor_csv, summarize_factors


class AdjustedResearchRunner:
    def __init__(
        self,
        target_date: date,
        start_date: date,
        end_date: date,
        data_dir: Path,
        config_dir: Path,
        output_dir: Path,
        price_sources: list[str] | None = None,
    ) -> None:
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        self.target_date = target_date
        self.start_date = start_date
        self.end_date = end_date
        self.data_dir = Path(data_dir)
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.price_sources = price_sources or ["raw", "qfq", "hfq"]
        self.config = load_project_config(self.config_dir)
        self.adapter = LocalCsvAdapter(self.data_dir)
        self.realism_bundle = OptionalRealismDataLoader(self.data_dir).load_all()
        self.daily_bars = self.adapter.load_daily_bars()
        self.stock_master = self.adapter.load_stock_master()
        self.financial_summary = self.adapter.load_financial_summary()
        self.announcement_events = self.adapter.load_announcement_events()
        self.factor_records_by_source: dict[str, list[Any]] = {}
        self.backtest_results_by_source: dict[str, BacktestResult] = {}

    def run(self) -> AdjustedResearchReport:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        validation_report = self.adapter.validate_all()
        if not validation_report.passed:
            now = datetime.now()
            steps = [
                AdjustedResearchStepResult(
                    name="validate-data",
                    status="FAILED",
                    started_at=now,
                    finished_at=datetime.now(),
                    duration_seconds=0.0,
                    output_paths=[],
                    summary={"errors": validation_report.errors},
                    error_message="data validation failed",
                )
            ]
            report = self._build_report(
                steps=steps,
                factor_comparisons=[],
                backtest_comparisons=[],
                status="FAILED",
                warnings=[],
            )
            self._save_report(report)
            return report

        steps: list[AdjustedResearchStepResult] = []
        for source in self.price_sources:
            if source == "raw":
                steps.append(self._run_step(f"build-adjusted-bars range {source}", lambda source=source: self._build_adjusted_range(source)))
            else:
                steps.append(self._run_step(f"build-adjusted-bars date {source}", lambda source=source: self._build_adjusted_date(source)))
                steps.append(self._run_step(f"build-adjusted-bars range {source}", lambda source=source: self._build_adjusted_range(source)))
        for source in self.price_sources:
            steps.append(self._run_step(f"compute-factors {source}", lambda source=source: self._compute_factors(source)))

        factor_comparisons: list[AdjustedFactorComparisonSummary] = []
        for right in (source for source in self.price_sources if source != "raw"):
            step = self._run_step(f"compare-factor-price-sources raw {right}", lambda right=right: self._compare_factors("raw", right))
            steps.append(step)
            if step.status == "SUCCESS" and step.output_paths:
                factor_comparisons.append(summarize_factor_comparison(Path(step.output_paths[0])))

        for source in self.price_sources:
            steps.append(self._run_step(f"run-backtest {source}", lambda source=source: self._run_backtest(source)))

        backtest_comparisons: list[AdjustedBacktestComparisonSummary] = []
        for right in (source for source in self.price_sources if source != "raw"):
            step = self._run_step(f"compare-backtest-price-sources raw {right}", lambda right=right: self._compare_backtests("raw", right))
            steps.append(step)
            if step.status == "SUCCESS" and step.output_paths:
                backtest_comparisons.append(summarize_backtest_comparison(Path(step.output_paths[0])))

        status = "FAILED" if any(step.status == "FAILED" for step in steps) else "SUCCESS"
        report = self._build_report(
            steps=steps,
            factor_comparisons=factor_comparisons,
            backtest_comparisons=backtest_comparisons,
            status=status,
            warnings=[],
        )
        warnings = build_adjusted_research_warnings(report)
        status = self._final_status(steps, warnings)
        report = report.model_copy(
            update={
                "status": status,
                "warning_items": warnings,
                "summary": self._summary(status, factor_comparisons, backtest_comparisons, warnings),
            }
        )
        self._save_report(report)
        return report

    def _run_step(self, name: str, action: Callable[[], dict[str, Any]]) -> AdjustedResearchStepResult:
        started_at = datetime.now()
        try:
            result = action()
        except Exception as exc:  # pragma: no cover - defensive boundary around report steps
            finished_at = datetime.now()
            return AdjustedResearchStepResult(
                name=name,
                status="FAILED",
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=(finished_at - started_at).total_seconds(),
                output_paths=[],
                summary={},
                error_message=str(exc),
            )
        finished_at = datetime.now()
        return AdjustedResearchStepResult(
            name=name,
            status="SUCCESS",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
            output_paths=[str(path) for path in result.get("output_paths", [])],
            summary=dict(result.get("summary", {})),
            error_message=None,
        )

    def _build_adjusted_date(self, source: str) -> dict[str, Any]:
        output_dir = self.output_dir / f"adjusted_date_{source}"
        return self._save_adjusted(source, output_dir, date_mode=True)

    def _build_adjusted_range(self, source: str) -> dict[str, Any]:
        output_dir = self.output_dir / f"adjusted_range_{source}"
        return self._save_adjusted(source, output_dir, date_mode=False)

    def _save_adjusted(self, source: str, output_dir: Path, date_mode: bool) -> dict[str, Any]:
        builder = AdjustedDailyBarBuilder(
            daily_bars=self.daily_bars,
            adjustment_factors=self.realism_bundle.adjustment_factors,
            corporate_actions=self.realism_bundle.corporate_actions,
            adj_type=source,
        )
        if date_mode:
            records, summary = builder.build_for_date(self.target_date)
        else:
            records, summary = builder.build_for_range(self.start_date, self.end_date)
        adjusted_csv = output_dir / "adjusted_daily_bar.csv"
        validation = validate_adjusted_records(records)
        summary = summary.model_copy(update={"output_path": str(adjusted_csv)})
        save_adjusted_daily_bar_csv(records, adjusted_csv)
        save_adjusted_summary_json(summary, output_dir / "adjusted_summary.json")
        save_adjusted_validation_json(validation, output_dir / "adjusted_validation.json")
        save_adjusted_report_md(summary, validation, output_dir / "adjusted_report.md")
        return {
            "output_paths": [
                adjusted_csv,
                output_dir / "adjusted_summary.json",
                output_dir / "adjusted_validation.json",
                output_dir / "adjusted_report.md",
            ],
            "summary": {
                "price_source": source,
                "total_records": summary.total_records,
                "adjusted_records": summary.adjusted_records,
                "invalid_records": summary.invalid_records,
                "warning_count": validation.warning_count,
                "error_count": validation.error_count,
            },
        }

    def _compute_factors(self, source: str) -> dict[str, Any]:
        records = FactorBuilder(
            config=self.config,
            daily_bars=self.daily_bars,
            stock_master=self.stock_master,
            price_source=source,
            adjustment_factors=self.realism_bundle.adjustment_factors if source != "raw" else None,
            corporate_actions=self.realism_bundle.corporate_actions if source != "raw" else None,
        ).build_for_date(self.target_date)
        self.factor_records_by_source[source] = records
        output_path = self.output_dir / f"factors_{source}" / "factor_daily.csv"
        save_factor_csv(records, output_path)
        summary = summarize_factors(records)
        summary.update(
            {
                "price_source": source,
                "adjusted_used_count": sum(1 for record in records if record.adjusted_used),
                "adjusted_issue_count": sum(1 for record in records if record.adjusted_quality_flags),
            }
        )
        return {"output_paths": [output_path], "summary": summary}

    def _compare_factors(self, left: str, right: str) -> dict[str, Any]:
        left_records = self.factor_records_by_source[left]
        right_records = self.factor_records_by_source[right]
        rows = _compare_factor_records(left_records, right_records)
        output_dir = self.output_dir / f"factor_compare_{left}_{right}"
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "factor_price_source_compare.csv"
        json_path = output_dir / "factor_price_source_compare.json"
        md_path = output_dir / "factor_price_source_compare.md"
        _save_factor_compare_csv(rows, csv_path)
        payload = {
            "trade_date": self.target_date.isoformat(),
            "left": left,
            "right": right,
            "total": len(rows),
            "changed_close_above_ma20": sum(1 for row in rows if row["close_above_ma20_changed"]),
            "changed_close_above_ma60": sum(1 for row in rows if row["close_above_ma60_changed"]),
            "rows": rows,
            "outputs": {"csv": str(csv_path), "json": str(json_path), "markdown": str(md_path)},
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(_render_factor_compare_md(payload), encoding="utf-8")
        return {
            "output_paths": [csv_path, json_path, md_path],
            "summary": {
                "left": left,
                "right": right,
                "total": len(rows),
                "changed_close_above_ma20": payload["changed_close_above_ma20"],
                "changed_close_above_ma60": payload["changed_close_above_ma60"],
            },
        }

    def _run_backtest(self, source: str) -> dict[str, Any]:
        result = BacktestEngine(
            config=self.config,
            stock_master=self.stock_master,
            daily_bars=self.daily_bars,
            financial_summary=self.financial_summary,
            announcement_events=self.announcement_events,
            price_source=source,
            adjustment_factors=self.realism_bundle.adjustment_factors if source != "raw" else None,
            corporate_actions=self.realism_bundle.corporate_actions if source != "raw" else None,
        ).run(self.start_date, self.end_date)
        self.backtest_results_by_source[source] = result
        output_dir = self.output_dir / f"backtest_{source}"
        _save_backtest_outputs(result, output_dir)
        metrics = result.metrics
        return {
            "output_paths": [
                output_dir / "metrics.json",
                output_dir / "daily_equity.csv",
                output_dir / "trades.csv",
                output_dir / "summary.md",
            ],
            "summary": {
                "price_source": source,
                "execution_price_source": "raw",
                "final_equity": metrics.final_equity,
                "total_return": metrics.total_return,
                "max_drawdown": metrics.max_drawdown,
                "sharpe": metrics.sharpe,
                "trade_count": metrics.trade_count,
                "adjusted_valuation_warning_count": len(result.valuation_warnings),
            },
        }

    def _compare_backtests(self, left: str, right: str) -> dict[str, Any]:
        comparison = _compare_backtest_results(
            self.backtest_results_by_source[left],
            self.backtest_results_by_source[right],
            left,
            right,
            self.start_date,
            self.end_date,
        )
        output_dir = self.output_dir / f"backtest_compare_{left}_{right}"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "backtest_price_source_compare.json"
        csv_path = output_dir / "backtest_price_source_compare.csv"
        md_path = output_dir / "backtest_price_source_compare.md"
        json_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_backtest_compare_csv(comparison, csv_path)
        _save_backtest_compare_md(comparison, md_path)
        diff = comparison["diff"]
        assert isinstance(diff, dict)
        return {
            "output_paths": [json_path, csv_path, md_path],
            "summary": {
                "left": left,
                "right": right,
                "total_return_diff": diff.get("total_return_diff"),
                "sharpe_diff": diff.get("sharpe_diff"),
                "final_equity_diff": diff.get("final_equity_diff"),
            },
        }

    def _build_report(
        self,
        steps: list[AdjustedResearchStepResult],
        factor_comparisons: list[AdjustedFactorComparisonSummary],
        backtest_comparisons: list[AdjustedBacktestComparisonSummary],
        status: str,
        warnings: list[str],
    ) -> AdjustedResearchReport:
        return AdjustedResearchReport(
            report_id=f"adjusted_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            data_dir=str(self.data_dir),
            config_dir=str(self.config_dir),
            target_date=self.target_date,
            start_date=self.start_date,
            end_date=self.end_date,
            status=status,  # type: ignore[arg-type]
            steps=steps,
            factor_comparisons=factor_comparisons,
            backtest_comparisons=backtest_comparisons,
            warning_items=warnings,
            output_dir=str(self.output_dir),
            summary=self._summary(status, factor_comparisons, backtest_comparisons, warnings),
        )

    def _save_report(self, report: AdjustedResearchReport) -> None:
        save_adjusted_research_report_json(report, self.output_dir / "adjusted_research_report.json")
        save_adjusted_research_report_md(report, self.output_dir / "adjusted_research_report.md")
        save_adjusted_research_summary_csv(report, self.output_dir / "adjusted_research_summary.csv")

    def _summary(
        self,
        status: str,
        factor_comparisons: list[AdjustedFactorComparisonSummary],
        backtest_comparisons: list[AdjustedBacktestComparisonSummary],
        warnings: list[str],
    ) -> str:
        return (
            f"status={status}; factor_comparisons={len(factor_comparisons)}; "
            f"backtest_comparisons={len(backtest_comparisons)}; warning_count={len(warnings)}"
        )

    def _final_status(self, steps: list[AdjustedResearchStepResult], warnings: list[str]) -> str:
        if any(step.status == "FAILED" for step in steps):
            return "FAILED"
        if any(item.startswith("WARNING:") for item in warnings):
            return "PARTIAL"
        return "SUCCESS"


def _save_backtest_outputs(result: BacktestResult, output_dir: Path) -> None:
    save_trades_csv(result.trades, output_dir / "trades.csv")
    save_daily_equity_csv(result.daily_equity, output_dir / "daily_equity.csv")
    save_metrics_json(result.metrics, output_dir / "metrics.json")
    save_backtest_summary_md(result, output_dir / "summary.md")


def _compare_backtest_results(
    left_result: BacktestResult,
    right_result: BacktestResult,
    left_source: str,
    right_source: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    left = left_result.metrics
    right = right_result.metrics
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "left": left_source,
        "right": right_source,
        "execution_price_source": "raw",
        "left_metrics": {
            "total_return": left.total_return,
            "annualized_return": left.annualized_return,
            "max_drawdown": left.max_drawdown,
            "sharpe": left.sharpe,
            "trade_count": left.trade_count,
            "final_equity": left.final_equity,
        },
        "right_metrics": {
            "total_return": right.total_return,
            "annualized_return": right.annualized_return,
            "max_drawdown": right.max_drawdown,
            "sharpe": right.sharpe,
            "trade_count": right.trade_count,
            "final_equity": right.final_equity,
        },
        "diff": {
            "total_return_diff": right.total_return - left.total_return,
            "annualized_return_diff": right.annualized_return - left.annualized_return,
            "max_drawdown_diff": right.max_drawdown - left.max_drawdown,
            "sharpe_diff": right.sharpe - left.sharpe,
            "trade_count_diff": right.trade_count - left.trade_count,
            "final_equity_diff": right.final_equity - left.final_equity,
        },
        "adjusted_research_note": (
            "raw vs qfq/hfq is a research valuation comparison only; execution constraints remain based on raw daily bars."
        ),
        "not_investment_advice": True,
        "no_live_trading": True,
        "left_adjusted_valuation_warning_count": len(left_result.valuation_warnings),
        "right_adjusted_valuation_warning_count": len(right_result.valuation_warnings),
    }


def _compare_factor_records(left_records: list[Any], right_records: list[Any]) -> list[dict[str, Any]]:
    left_by_code = {record.ts_code: record for record in left_records}
    right_by_code = {record.ts_code: record for record in right_records}
    rows: list[dict[str, Any]] = []
    for ts_code in sorted(set(left_by_code) | set(right_by_code)):
        left = left_by_code.get(ts_code)
        right = right_by_code.get(ts_code)
        rows.append(
            {
                "ts_code": ts_code,
                "left_price_source": left.price_source if left is not None else None,
                "right_price_source": right.price_source if right is not None else None,
                "left_is_computable": left.is_computable if left is not None else None,
                "right_is_computable": right.is_computable if right is not None else None,
                "momentum_5d_diff": _numeric_diff(left, right, "momentum_5d"),
                "momentum_20d_diff": _numeric_diff(left, right, "momentum_20d"),
                "momentum_60d_diff": _numeric_diff(left, right, "momentum_60d"),
                "ma20_diff": _numeric_diff(left, right, "ma20"),
                "ma60_diff": _numeric_diff(left, right, "ma60"),
                "volatility_20d_diff": _numeric_diff(left, right, "volatility_20d"),
                "max_drawdown_20d_diff": _numeric_diff(left, right, "max_drawdown_20d"),
                "close_above_ma20_changed": _bool_changed(left, right, "close_above_ma20"),
                "close_above_ma60_changed": _bool_changed(left, right, "close_above_ma60"),
                "left_missing_reasons": ";".join(left.missing_reasons) if left is not None else "",
                "right_missing_reasons": ";".join(right.missing_reasons) if right is not None else "",
            }
        )
    return rows


def _numeric_diff(left: object | None, right: object | None, field_name: str) -> float | None:
    if left is None or right is None:
        return None
    left_value = getattr(left, field_name)
    right_value = getattr(right, field_name)
    if left_value is None or right_value is None:
        return None
    return right_value - left_value


def _bool_changed(left: object | None, right: object | None, field_name: str) -> bool | None:
    if left is None or right is None:
        return None
    left_value = getattr(left, field_name)
    right_value = getattr(right, field_name)
    if left_value is None or right_value is None:
        return None
    return left_value != right_value


def _save_factor_compare_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    fieldnames = [
        "ts_code",
        "left_price_source",
        "right_price_source",
        "left_is_computable",
        "right_is_computable",
        "momentum_5d_diff",
        "momentum_20d_diff",
        "momentum_60d_diff",
        "ma20_diff",
        "ma60_diff",
        "volatility_20d_diff",
        "max_drawdown_20d_diff",
        "close_above_ma20_changed",
        "close_above_ma60_changed",
        "left_missing_reasons",
        "right_missing_reasons",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _render_factor_compare_md(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    assert isinstance(rows, list)
    largest_rows = sorted(rows, key=_row_max_abs_diff, reverse=True)[:10]
    lines = [
        "# Factor Price Source Comparison",
        "",
        f"- trade_date: {payload['trade_date']}",
        f"- left: {payload['left']}",
        f"- right: {payload['right']}",
        f"- rows: {payload['total']}",
        "",
        "This report compares factor_daily values built from two price_source settings. It is for research only, does not constitute investment advice, and does not place orders automatically.",
        "",
        "## Largest Differences",
        "",
        "| ts_code | max_abs_diff | ma20_diff | ma60_diff | momentum_20d_diff | volatility_20d_diff |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in largest_rows:
        assert isinstance(row, dict)
        lines.append(
            "| "
            f"{row['ts_code']} | "
            f"{_format_optional_float(_row_max_abs_diff(row))} | "
            f"{_format_optional_float(row['ma20_diff'])} | "
            f"{_format_optional_float(row['ma60_diff'])} | "
            f"{_format_optional_float(row['momentum_20d_diff'])} | "
            f"{_format_optional_float(row['volatility_20d_diff'])} |"
        )
    return "\n".join(lines) + "\n"


def _row_max_abs_diff(row: dict[str, Any]) -> float:
    fields = [
        "momentum_5d_diff",
        "momentum_20d_diff",
        "momentum_60d_diff",
        "ma20_diff",
        "ma60_diff",
        "volatility_20d_diff",
        "max_drawdown_20d_diff",
    ]
    values = [abs(value) for field in fields if isinstance((value := row.get(field)), int | float)]
    return max(values) if values else 0.0


def _save_backtest_compare_csv(comparison: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    diff = comparison["diff"]
    assert isinstance(diff, dict)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "diff"])
        writer.writeheader()
        for key, value in diff.items():
            writer.writerow({"metric": key, "diff": value})


def _save_backtest_compare_md(comparison: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    diff = comparison["diff"]
    assert isinstance(diff, dict)
    lines = [
        "# Backtest Price Source Compare",
        "",
        f"- Start date: {comparison['start_date']}",
        f"- End date: {comparison['end_date']}",
        f"- Left: {comparison['left']}",
        f"- Right: {comparison['right']}",
        "- Execution constraints remain based on raw daily bars.",
        "- raw vs qfq/hfq is a research valuation comparison only.",
        "- Adjusted valuation is not a live trading execution price.",
        "- This is not investment advice.",
        "- The system does not place orders automatically.",
        "",
        "## Diffs",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in diff.items())
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_optional_float(value: object) -> str:
    return "-" if not isinstance(value, int | float) or isinstance(value, bool) else f"{value:.8g}"
