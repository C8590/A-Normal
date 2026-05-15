from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha.experiments.hashing import create_experiment_id, hash_config_dir
from ashare_alpha.experiments.models import ExperimentArtifact, ExperimentMetric, ExperimentRecord
from ashare_alpha.experiments.registry import ExperimentRegistry


def infer_data_version_from_dir(data_dir: Path) -> tuple[str | None, str | None]:
    path = Path(data_dir)
    parts = path.parts
    normalized = [part.replace("\\", "/") for part in parts]
    for marker in ("imports", "materialized"):
        if marker in normalized:
            index = normalized.index(marker)
            if len(parts) > index + 2 and index > 0 and normalized[index - 1] == "data":
                return parts[index + 1], parts[index + 2]
    if Path(*parts[-3:]).as_posix() == "data/sample/ashare_alpha":
        return "local_csv", "sample"
    return None, None


def discover_artifacts(output_dir: Path) -> list[ExperimentArtifact]:
    base = Path(output_dir)
    if not base.exists():
        return []
    artifacts: list[ExperimentArtifact] = []
    for path in _iter_artifact_paths(base):
        artifacts.append(
            ExperimentArtifact(
                name=path.name,
                path=str(path),
                artifact_type=_artifact_type(path),
            )
        )
    return artifacts


def extract_metrics_from_output(output_dir: Path, command: str) -> list[ExperimentMetric]:
    base = Path(output_dir)
    if not base.exists():
        return []
    normalized = command.strip().lower()
    if normalized in {"run-backtest", "backtest-report"}:
        return _metrics_from_mapping(base / "metrics.json", _BACKTEST_METRICS, "backtest")
    if normalized == "run-pipeline":
        return _metrics_from_mapping(base / "manifest.json", _PIPELINE_METRICS, "pipeline")
    if normalized == "train-probability-model":
        return _probability_metrics(base / "metrics.json")
    if normalized == "daily-report":
        return _daily_report_metrics(base / "daily_report.json")
    return []


class ExperimentRecorder:
    def __init__(self, registry: ExperimentRegistry) -> None:
        self.registry = registry

    def record_completed_run(
        self,
        command: str,
        command_args: dict[str, object],
        status: str,
        output_dir: Path,
        data_dir: Path | None,
        config_dir: Path | None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> ExperimentRecord:
        output_path = Path(output_dir)
        if not output_path.exists():
            raise ValueError(f"output-dir does not exist: {output_path}")
        data_source, data_version = infer_data_version_from_dir(data_dir) if data_dir is not None else (None, None)
        config_hash = hash_config_dir(config_dir) if config_dir is not None and Path(config_dir).exists() else None
        created_at = datetime.now()
        experiment_id = create_experiment_id(command, command_args, config_hash, data_version, created_at)
        record = ExperimentRecord(
            experiment_id=experiment_id,
            created_at=created_at,
            command=command,
            command_args=_jsonable(command_args),
            data_dir=str(data_dir) if data_dir is not None else None,
            config_dir=str(config_dir) if config_dir is not None else None,
            output_dir=str(output_path),
            data_source=data_source,
            data_version=data_version,
            config_hash=config_hash,
            code_version=None,
            status=status,
            metrics=extract_metrics_from_output(output_path, command),
            artifacts=discover_artifacts(output_path),
            notes=notes,
            tags=tags or [],
        )
        return self.registry.add(record)


_BACKTEST_METRICS = (
    "total_return",
    "annualized_return",
    "max_drawdown",
    "sharpe",
    "win_rate",
    "turnover",
    "trade_count",
    "filled_trade_count",
    "rejected_trade_count",
)
_PIPELINE_METRICS = (
    "total_stocks",
    "allowed_universe_count",
    "buy_count",
    "watch_count",
    "block_count",
    "high_risk_count",
    "probability_predictable_count",
)


def _iter_artifact_paths(base: Path) -> list[Path]:
    paths: list[Path] = []
    for child in sorted(base.iterdir()):
        paths.append(child)
        if child.is_dir():
            paths.extend(sorted(item for item in child.iterdir() if item.is_file() or item.is_dir()))
    return paths


def _artifact_type(path: Path) -> str:
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix == ".md":
        return "markdown"
    return "other"


def _metrics_from_mapping(path: Path, names: tuple[str, ...], category: str) -> list[ExperimentMetric]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return []
    return [
        ExperimentMetric(name=name, value=payload.get(name), category=category)
        for name in names
        if name in payload
    ]


def _probability_metrics(path: Path) -> list[ExperimentMetric]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        return []
    metrics: list[ExperimentMetric] = []
    for row in payload:
        if not isinstance(row, dict) or "horizon" not in row:
            continue
        horizon = row["horizon"]
        for name in ("accuracy", "precision", "recall", "auc", "brier_score", "actual_win_rate"):
            if name in row:
                metrics.append(ExperimentMetric(name=f"{name}_{horizon}d", value=row.get(name), category="probability"))
    return metrics


def _daily_report_metrics(path: Path) -> list[ExperimentMetric]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else payload
    mapping = {
        "total_stocks": "total_stocks",
        "buy_count": "buy_count",
        "watch_count": "watch_count",
        "block_count": "block_count",
        "high_risk_count": "high_risk_count",
    }
    return [
        ExperimentMetric(name=name, value=summary.get(source_key), category="daily_report")
        for name, source_key in mapping.items()
        if source_key in summary
    ]


def _read_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
