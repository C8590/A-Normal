from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_alpha.gates.models import LoadedArtifact


_FILENAME_TYPES = {
    "quality_report.json": "data_quality",
    "audit_report.json": "leakage_audit",
    "security_scan_report.json": "security",
    "manifest.json": "pipeline",
    "metrics.json": "backtest",
    "sweep_result.json": "sweep",
    "walkforward_result.json": "walkforward",
    "candidate_selection.json": "candidate_selection",
    "adjusted_research_report.json": "adjusted_research",
}


class ResearchArtifactLoader:
    def infer_artifact_type(self, path: Path) -> str:
        path = Path(path)
        inferred = _FILENAME_TYPES.get(path.name)
        if inferred:
            return inferred
        return "unknown"

    def load_artifact(self, path: Path) -> dict[str, Any]:
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"artifact JSON must be an object: {path}")
        return payload

    def load_many(self, paths: list[Path]) -> list[LoadedArtifact]:
        artifacts: list[LoadedArtifact] = []
        for path in paths:
            artifact_type = self.infer_artifact_type(path)
            try:
                data = self.load_artifact(path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                data = {"_loader_error": str(exc)}
            artifacts.append(LoadedArtifact(artifact_type=artifact_type, path=str(path), data=data))
        return artifacts
