from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_alpha.experiments import load_experiment_record
from ashare_alpha.experiments.models import ExperimentRecord
from ashare_alpha.sweeps import load_sweep_result_json
from ashare_alpha.sweeps.models import SweepResult
from ashare_alpha.walkforward import load_walkforward_result_json
from ashare_alpha.walkforward.models import WalkForwardResult

from ashare_alpha.candidates.models import CandidateRecord


class CandidateLoader:
    def load_candidates_from_sweep(self, path: Path) -> list[CandidateRecord]:
        return load_candidates_from_sweep(path)

    def load_candidates_from_walkforward(self, path: Path) -> list[CandidateRecord]:
        return load_candidates_from_walkforward(path)

    def load_candidate_from_experiment(self, path: Path) -> CandidateRecord:
        return load_candidate_from_experiment(path)


def load_candidates_from_sweep(path: Path) -> list[CandidateRecord]:
    result = load_sweep_result_json(Path(path))
    return [_candidate_from_sweep_run(result, Path(path), run) for run in result.runs]


def load_candidates_from_walkforward(path: Path) -> list[CandidateRecord]:
    result = load_walkforward_result_json(Path(path))
    tags = [f"command:{result.command}"]
    fold_experiment_ids = [fold.experiment_id for fold in result.folds if fold.experiment_id]
    metrics = dict(result.stability_metrics)
    if fold_experiment_ids:
        metrics["fold_experiment_ids"] = fold_experiment_ids
    if "success_fold_count" not in metrics:
        metrics["success_fold_count"] = result.success_count
    if "fold_count" not in metrics:
        metrics["fold_count"] = result.fold_count
    metrics["failed_fold_count"] = result.failed_count
    metrics["skipped_fold_count"] = result.skipped_count
    metrics["total_trade_count"] = _sum_fold_metric(result, ("trade_count", "filled_trade_count"))
    output_dir = str(Path(path).parent)
    return [
        CandidateRecord(
            candidate_id=f"walkforward:{result.walkforward_id}",
            name=result.name,
            source_type="walkforward",
            source_path=str(path),
            experiment_id=fold_experiment_ids[0] if len(fold_experiment_ids) == 1 else None,
            config_dir=None,
            output_dir=output_dir,
            metrics=metrics,
            warnings=list(result.overfit_warnings),
            tags=tags,
        )
    ]


def load_candidate_from_experiment(path: Path) -> CandidateRecord:
    record = load_experiment_record(Path(path))
    return _candidate_from_experiment_record(record, Path(path))


def _candidate_from_sweep_run(result: SweepResult, path: Path, run) -> CandidateRecord:
    warnings: list[str] = []
    if run.status == "FAILED":
        warnings.append("候选运行失败，指标为空，仅保留用于拒绝判断。")
    elif run.status == "PARTIAL":
        warnings.append("候选运行部分成功，需要人工复核。")
    if run.error_message:
        warnings.append(str(run.error_message))
    metrics = dict(run.metrics) if run.status in {"SUCCESS", "PARTIAL"} else {}
    return CandidateRecord(
        candidate_id=f"sweep:{result.sweep_id}:{run.variant_name}",
        name=run.variant_name,
        source_type="sweep",
        source_path=str(path),
        experiment_id=run.experiment_id,
        config_dir=run.config_dir,
        output_dir=run.output_dir,
        metrics=metrics,
        warnings=warnings,
        tags=[f"sweep:{result.sweep_name}", f"status:{run.status}", f"command:{result.command}"],
    )


def _candidate_from_experiment_record(record: ExperimentRecord, path: Path) -> CandidateRecord:
    warnings: list[str] = []
    if record.status == "FAILED":
        warnings.append("实验记录状态为 FAILED。")
    elif record.status == "PARTIAL":
        warnings.append("实验记录状态为 PARTIAL，需要人工复核。")
    metrics = {metric.name: metric.value for metric in record.metrics}
    if record.config_hash:
        metrics["config_hash"] = record.config_hash
    return CandidateRecord(
        candidate_id=f"experiment:{record.experiment_id}",
        name=record.experiment_id,
        source_type="experiment",
        source_path=str(path),
        experiment_id=record.experiment_id,
        config_dir=record.config_dir,
        output_dir=record.output_dir,
        metrics=metrics,
        warnings=warnings,
        tags=[*record.tags, f"command:{record.command}", f"status:{record.status}"],
    )


def _sum_fold_metric(result: WalkForwardResult, names: tuple[str, ...]) -> int:
    total = 0
    for fold in result.folds:
        for name in names:
            value = _number(fold.metrics.get(name))
            if value is not None:
                total += int(value)
                break
    return total


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None
