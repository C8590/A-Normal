from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.walkforward.models import WalkForwardResult


_FOLD_METRIC_COLUMNS = (
    "total_return",
    "annualized_return",
    "max_drawdown",
    "sharpe",
    "win_rate",
    "turnover",
    "trade_count",
    "filled_trade_count",
    "rejected_trade_count",
    "success_count",
    "failed_count",
    "best_total_return",
    "mean_total_return",
    "worst_max_drawdown",
)


def save_walkforward_result_json(result: WalkForwardResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_walkforward_result_json(path: Path) -> WalkForwardResult:
    return WalkForwardResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_walkforward_summary_md(result: WalkForwardResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_summary(result), encoding="utf-8")


def save_fold_metrics_csv(result: WalkForwardResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "fold_index",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "status",
        "experiment_id",
        "output_dir",
        *_FOLD_METRIC_COLUMNS,
        "error_message",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for fold in result.folds:
            row = {
                "fold_index": fold.fold_index,
                "train_start": fold.train_start.isoformat() if fold.train_start else "",
                "train_end": fold.train_end.isoformat() if fold.train_end else "",
                "test_start": fold.test_start.isoformat(),
                "test_end": fold.test_end.isoformat(),
                "status": fold.status,
                "experiment_id": fold.experiment_id or "",
                "output_dir": fold.output_dir or "",
                "error_message": fold.error_message or "",
            }
            for column in _FOLD_METRIC_COLUMNS:
                row[column] = fold.metrics.get(column, "")
            writer.writerow(row)


def _render_summary(result: WalkForwardResult) -> str:
    lines = [
        "# Walk-forward 样本外验证报告",
        "",
        "## 1. 基本信息",
        f"- walkforward_id: {result.walkforward_id}",
        f"- name: {result.name}",
        f"- command: {result.command}",
        f"- start_date / end_date: {result.start_date.isoformat()} / {result.end_date.isoformat()}",
        f"- fold_count: {result.fold_count}",
        "",
        "## 2. Fold 结果",
        "| fold | test_start | test_end | status | experiment_id | total_return | max_drawdown | sharpe | trade_count | error |",
        "| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for fold in result.folds:
        lines.append(
            "| "
            f"{fold.fold_index} | "
            f"{fold.test_start.isoformat()} | "
            f"{fold.test_end.isoformat()} | "
            f"{fold.status} | "
            f"{fold.experiment_id or '-'} | "
            f"{_format_metric(fold.metrics.get('total_return'))} | "
            f"{_format_metric(fold.metrics.get('max_drawdown'))} | "
            f"{_format_metric(fold.metrics.get('sharpe'))} | "
            f"{_format_metric(fold.metrics.get('trade_count'))} | "
            f"{_escape_md(fold.error_message or '-')} |"
        )

    lines.extend(["", "## 3. 稳定性指标"])
    for key, value in result.stability_metrics.items():
        lines.append(f"- {key}: {_format_metric(value)}")

    lines.extend(["", "## 4. 过拟合风险提示"])
    if result.overfit_warnings:
        lines.extend(f"- {warning}" for warning in result.overfit_warnings)
    else:
        lines.append("- 未触发主要过拟合风险提示")

    lines.extend(["", "## 5. 输出目录"])
    for fold in result.folds:
        lines.append(f"- fold_{fold.fold_index:03d}: {fold.output_dir or '-'}")

    lines.extend(
        [
            "",
            "## 6. 说明",
            "- 仅用于研究验证。",
            "- 不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "",
            result.summary,
            "",
        ]
    )
    return "\n".join(lines)


def _format_metric(value: object) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
