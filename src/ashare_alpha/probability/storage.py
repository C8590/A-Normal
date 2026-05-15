from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ashare_alpha.probability.models import (
    ProbabilityDatasetRecord,
    ProbabilityMetrics,
    ProbabilityModel,
    ProbabilityPredictionRecord,
    ProbabilityTrainingResult,
)


def save_probability_dataset_csv(records: list[ProbabilityDatasetRecord], output_path: Path) -> None:
    _save_model_csv(records, output_path, list(ProbabilityDatasetRecord.model_fields))


def save_probability_predictions_csv(records: list[ProbabilityPredictionRecord], output_path: Path) -> None:
    _save_model_csv(records, output_path, list(ProbabilityPredictionRecord.model_fields))


def save_probability_model_json(model: ProbabilityModel, output_path: Path) -> None:
    _write_json(model.model_dump(mode="json"), output_path)


def load_probability_model_json(path: Path) -> ProbabilityModel:
    if not path.exists():
        raise ValueError(f"model.json not found: {path}")
    return ProbabilityModel.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_probability_metrics_json(metrics: list[ProbabilityMetrics], output_path: Path) -> None:
    _write_json([metric.model_dump(mode="json") for metric in metrics], output_path)


def save_probability_summary_md(result: ProbabilityTrainingResult, output_path: Path) -> None:
    model = result.model
    lines = [
        "# 概率模型训练摘要",
        "",
        "本模型仅用于研究，不构成投资建议，不连接券商接口，也不会自动下单。",
        "",
        "## 1. 训练区间",
        f"- 训练开始：{model.train_start_date.isoformat()}",
        f"- 训练结束：{model.train_end_date.isoformat()}",
        f"- 测试开始：{model.test_start_date.isoformat() if model.test_start_date else '无'}",
        f"- 测试结束：{model.test_end_date.isoformat() if model.test_end_date else '无'}",
        "",
        "## 2. 数据摘要",
        f"- 数据集行数：{result.dataset_rows}",
        f"- 训练行数：{result.train_rows}",
        f"- 测试行数：{result.test_rows}",
        f"- 跳过行数：{result.skipped_rows}",
        "",
        "## 3. 分周期指标",
        "| 周期 | 样本数 | 实际胜率 | Accuracy | AUC | Brier |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in result.metrics:
        lines.append(
            f"| {metric.horizon} | {metric.sample_count} | {_pct(metric.actual_win_rate)} | "
            f"{_pct(metric.accuracy)} | {_number(metric.auc)} | {_number(metric.brier_score)} |"
        )
    lines.extend(["", "## 4. 说明", result.summary, ""])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _save_model_csv(records: list[BaseModel], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: _csv_value(value) for key, value in record.model_dump(mode="json").items()})


def _write_json(payload: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.2%}"


def _number(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"
