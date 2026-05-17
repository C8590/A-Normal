from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ashare_alpha.dashboard.models import DashboardArtifact, DashboardIndex


class DashboardScanner:
    def __init__(self, outputs_root: Path = Path("outputs")) -> None:
        self.outputs_root = Path(outputs_root)

    def scan(self) -> DashboardIndex:
        if not self.outputs_root.exists():
            raise ValueError(f"outputs_root does not exist: {self.outputs_root}")
        artifacts: list[DashboardArtifact] = []
        artifacts.extend(self._scan_pattern("pipeline", self.outputs_root / "pipelines", "**/manifest.json", self._pipeline_artifact))
        artifacts.extend(self._scan_pattern("backtest", self.outputs_root / "backtests", "**/metrics.json", self._backtest_artifact))
        artifacts.extend(
            self._scan_pattern(
                "adjusted_research",
                self.outputs_root / "adjusted_research",
                "**/adjusted_research_report.json",
                self._adjusted_research_artifact,
            )
        )
        artifacts.extend(
            self._scan_pattern(
                "research_gate",
                self.outputs_root / "gates",
                "**/research_gate_report.json",
                self._research_gate_artifact,
            )
        )
        artifacts.extend(
            self._scan_pattern(
                "research_gate",
                self.outputs_root / "pipelines",
                "**/gates/research_gate_report.json",
                self._research_gate_artifact,
            )
        )
        artifacts.extend(self._scan_pattern("sweep", self.outputs_root / "sweeps", "**/sweep_result.json", self._sweep_artifact))
        artifacts.extend(
            self._scan_pattern("walkforward", self.outputs_root / "walkforward", "**/walkforward_result.json", self._walkforward_artifact)
        )
        artifacts.extend(
            self._scan_pattern("experiment", self.outputs_root / "experiments" / "records", "*.json", self._experiment_artifact)
        )
        artifacts.extend(
            self._scan_pattern(
                "candidate_selection",
                self.outputs_root / "candidates",
                "**/candidate_selection.json",
                self._candidate_selection_artifact,
            )
        )
        artifacts.extend(self._scan_pattern("quality_report", self.outputs_root / "quality", "**/quality_report.json", self._quality_artifact))
        artifacts.extend(self._scan_pattern("leakage_audit", self.outputs_root / "audit", "**/audit_report.json", self._audit_artifact))
        artifacts.extend(
            self._scan_pattern("security_scan", self.outputs_root / "security", "**/security_scan_report.json", self._security_artifact)
        )
        artifacts.extend(self._scan_pattern("probability_model", self.outputs_root / "models", "**/model.json", self._probability_artifact))
        imports_root = self.outputs_root.parent / "data" / "imports"
        artifacts.extend(self._scan_pattern("quality_report", imports_root, "**/quality_report.json", self._quality_artifact))
        artifacts.extend(self._scan_pattern("leakage_audit", imports_root, "**/audit_report.json", self._audit_artifact))

        artifacts = sorted(artifacts, key=lambda item: item.created_at or datetime.min, reverse=True)
        counts: dict[str, int] = {}
        for artifact in artifacts:
            counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1
        return DashboardIndex(
            generated_at=datetime.now(),
            outputs_root=str(self.outputs_root),
            artifact_count=len(artifacts),
            artifacts_by_type=counts,
            artifacts=artifacts,
        )

    def _scan_pattern(self, artifact_type: str, root: Path, pattern: str, factory) -> list[DashboardArtifact]:
        if not root.exists():
            return []
        artifacts: list[DashboardArtifact] = []
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                payload = _read_json(path)
                artifacts.append(factory(path, payload))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                artifacts.append(self._unknown_artifact(path, artifact_type, str(exc)))
        return artifacts

    def _pipeline_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(
            payload,
            (
                "pipeline_date",
                "status",
                "buy_count",
                "watch_count",
                "block_count",
                "high_risk_count",
                "market_regime",
                "probability_predictable_count",
            ),
        )
        name = str(payload.get("pipeline_date") or path.parent.name)
        return _artifact("pipeline", f"pipeline:{path.parent.name}", name, path, _created_at(path, payload), payload.get("status"), summary)

    def _backtest_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(
            payload,
            (
                "start_date",
                "end_date",
                "final_equity",
                "total_return",
                "max_drawdown",
                "sharpe",
                "trade_count",
                "filled_trade_count",
                "rejected_trade_count",
            ),
        )
        name = f"{payload.get('start_date', path.parent.name)}..{payload.get('end_date', '')}".rstrip(".")
        return _artifact("backtest", f"backtest:{path.parent.name}", name, path, _created_at(path, payload), None, summary)

    def _adjusted_research_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(
            payload,
            (
                "report_id",
                "target_date",
                "start_date",
                "end_date",
                "status",
                "output_dir",
                "summary",
            ),
        )
        factor_comparisons = payload.get("factor_comparisons", [])
        backtest_comparisons = payload.get("backtest_comparisons", [])
        warning_items = payload.get("warning_items", [])
        summary["factor_comparison_count"] = len(factor_comparisons) if isinstance(factor_comparisons, list) else 0
        summary["backtest_comparison_count"] = len(backtest_comparisons) if isinstance(backtest_comparisons, list) else 0
        summary["warning_count"] = len(warning_items) if isinstance(warning_items, list) else 0
        summary["warning_items"] = warning_items if isinstance(warning_items, list) else []
        return _artifact(
            "adjusted_research",
            f"adjusted_research:{payload.get('report_id', path.parent.name)}",
            str(payload.get("report_id") or path.parent.name),
            path,
            _created_at(path, payload),
            payload.get("status"),
            summary,
            related_paths=[str(path.parent / "adjusted_research_report.md"), str(path.parent / "adjusted_research_summary.csv")],
        )

    def _research_gate_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(
            payload,
            (
                "report_id",
                "overall_decision",
                "issue_count",
                "blocker_count",
                "warning_count",
                "info_count",
                "summary",
            ),
        )
        return _artifact(
            "research_gate",
            f"research_gate:{payload.get('report_id', path.parent.name)}",
            str(payload.get("report_id") or path.parent.name),
            path,
            _created_at(path, payload),
            payload.get("overall_decision"),
            summary,
            related_paths=[str(path.parent / "research_gate_report.md"), str(path.parent / "research_gate_issues.csv")],
        )

    def _sweep_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(payload, ("sweep_id", "sweep_name", "command", "total_variants", "success_count", "failed_count"))
        status = "FAILED" if _number(payload.get("failed_count"), 0) == _number(payload.get("total_variants"), -1) else "SUCCESS"
        if _number(payload.get("failed_count"), 0) > 0 and status == "SUCCESS":
            status = "PARTIAL"
        return _artifact(
            "sweep",
            f"sweep:{payload.get('sweep_id', path.parent.name)}",
            str(payload.get("sweep_name") or path.parent.name),
            path,
            _created_at(path, payload, "generated_at"),
            status,
            summary,
        )

    def _walkforward_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(payload, ("walkforward_id", "name", "command", "fold_count", "success_count", "failed_count"))
        summary["stability_metrics"] = payload.get("stability_metrics", {})
        summary["overfit_warnings"] = payload.get("overfit_warnings", [])
        status = "FAILED" if _number(payload.get("failed_count"), 0) == _number(payload.get("fold_count"), -1) else "SUCCESS"
        if _number(payload.get("failed_count"), 0) > 0 and status == "SUCCESS":
            status = "PARTIAL"
        return _artifact(
            "walkforward",
            f"walkforward:{payload.get('walkforward_id', path.parent.name)}",
            str(payload.get("name") or path.parent.name),
            path,
            _created_at(path, payload, "generated_at"),
            status,
            summary,
        )

    def _experiment_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        metrics = payload.get("metrics", [])
        summary = _pick(payload, ("experiment_id", "command", "status", "data_source", "data_version", "tags"))
        summary["metrics"] = _metric_list_to_mapping(metrics)
        return _artifact(
            "experiment",
            f"experiment:{payload.get('experiment_id', path.stem)}",
            str(payload.get("experiment_id") or path.stem),
            path,
            _created_at(path, payload, "created_at"),
            payload.get("status"),
            summary,
        )

    def _candidate_selection_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        scores = payload.get("scores", [])
        summary = _pick(payload, ("selection_id", "total_candidates", "advance_count", "review_count", "reject_count"))
        summary["top_scores"] = scores[:10] if isinstance(scores, list) else []
        return _artifact(
            "candidate_selection",
            f"candidate_selection:{payload.get('selection_id', path.parent.name)}",
            str(payload.get("selection_id") or path.parent.name),
            path,
            _created_at(path, payload, "generated_at"),
            None,
            summary,
        )

    def _quality_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(payload, ("passed", "total_issues", "error_count", "warning_count", "info_count", "data_dir", "source_name", "data_version"))
        status = "SUCCESS" if payload.get("passed") is True else "FAILED"
        return _artifact("quality_report", f"quality_report:{path.parent.name}:{path.name}", path.parent.name, path, _created_at(path, payload), status, summary)

    def _audit_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(
            payload,
            ("passed", "total_issues", "error_count", "warning_count", "info_count", "audit_date", "start_date", "end_date", "data_dir"),
        )
        status = "SUCCESS" if payload.get("passed") is True else "FAILED"
        return _artifact("leakage_audit", f"leakage_audit:{path.parent.name}:{path.name}", path.parent.name, path, _created_at(path, payload), status, summary)

    def _security_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        summary = _pick(payload, ("passed", "total_issues", "error_count", "warning_count", "info_count", "config_dir"))
        status = "SUCCESS" if payload.get("passed") is True else "FAILED"
        return _artifact("security_scan", f"security_scan:{path.parent.name}:{path.name}", path.parent.name, path, _created_at(path, payload), status, summary)

    def _probability_artifact(self, path: Path, payload: dict[str, Any]) -> DashboardArtifact:
        metrics_path = path.parent / "metrics.json"
        metrics_payload: Any = None
        if metrics_path.exists():
            try:
                metrics_payload = _read_json(metrics_path)
            except ValueError:
                metrics_payload = None
        summary = {
            "model_path": str(path),
            "metrics": metrics_payload if metrics_payload is not None else [],
        }
        for key in ("created_at", "start_date", "end_date", "horizons"):
            if key in payload:
                summary[key] = payload.get(key)
        related_paths = [str(metrics_path)] if metrics_path.exists() else []
        return _artifact(
            "probability_model",
            f"probability_model:{path.parent.name}",
            path.parent.name,
            path,
            _created_at(path, payload),
            None,
            summary,
            related_paths=related_paths,
        )

    def _unknown_artifact(self, path: Path, expected_type: str, error: str) -> DashboardArtifact:
        return DashboardArtifact(
            artifact_id=f"unknown:{expected_type}:{path}",
            artifact_type="unknown",
            name=path.name,
            path=str(path),
            created_at=_mtime(path),
            status="FAILED",
            summary={"expected_type": expected_type, "error": error},
            related_paths=[],
        )


def _artifact(
    artifact_type: str,
    artifact_id: str,
    name: str,
    path: Path,
    created_at: datetime | None,
    status: Any,
    summary: dict[str, Any],
    related_paths: list[str] | None = None,
) -> DashboardArtifact:
    return DashboardArtifact(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        name=name,
        path=str(path),
        created_at=created_at,
        status=str(status) if status is not None else None,
        summary=summary,
        related_paths=related_paths or [],
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _pick(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys if key in payload}


def _created_at(path: Path, payload: dict[str, Any], preferred_key: str = "generated_at") -> datetime | None:
    for key in (preferred_key, "created_at", "generated_at", "pipeline_date", "start_date"):
        value = payload.get(key)
        parsed = _parse_datetime(value)
        if parsed is not None:
            return parsed
    return _mtime(path)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(tzinfo=None)
    except OSError:
        return None


def _number(value: Any, default: float) -> float:
    if isinstance(value, bool) or value in {None, ""}:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric_list_to_mapping(metrics: Any) -> dict[str, Any]:
    if not isinstance(metrics, list):
        return {}
    result: dict[str, Any] = {}
    for item in metrics:
        if isinstance(item, dict) and item.get("name"):
            result[str(item["name"])] = item.get("value")
    return result
