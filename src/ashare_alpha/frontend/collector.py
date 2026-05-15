from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha import __version__
from ashare_alpha.dashboard import DashboardScanner, build_dashboard_summary
from ashare_alpha.dashboard.models import DashboardArtifact, DashboardIndex
from ashare_alpha.frontend.models import FrontendData


def collect_frontend_data(outputs_root: Path = Path("outputs"), version: str = __version__) -> FrontendData:
    root = Path(outputs_root)
    if root.exists():
        index = DashboardScanner(root).scan()
        summary = build_dashboard_summary(index)
        extra_warnings: list[dict[str, Any]] = []
    else:
        index = DashboardIndex(
            generated_at=datetime.now(),
            outputs_root=str(root),
            artifact_count=0,
            artifacts_by_type={},
            artifacts=[],
        )
        summary = build_dashboard_summary(index)
        extra_warnings = [
            {
                "artifact_id": "outputs_root",
                "artifact_type": "frontend",
                "name": "outputs_root",
                "path": str(root),
                "message": f"outputs_root does not exist: {root}",
            }
        ]
    return FrontendData(
        generated_at=datetime.now(),
        outputs_root=str(root),
        version=version,
        summary={
            "artifact_count": index.artifact_count,
            "artifacts_by_type": index.artifacts_by_type,
            "warning_count": len(summary.warning_items) + len(extra_warnings),
            "summary_text": summary.summary_text,
        },
        latest_pipeline=_artifact_dict(summary.latest_pipeline),
        latest_backtest=_artifact_dict(summary.latest_backtest),
        latest_sweep=_artifact_dict(summary.latest_sweep),
        latest_walkforward=_artifact_dict(summary.latest_walkforward),
        latest_candidate_selection=_artifact_dict(summary.latest_candidate_selection),
        recent_experiments=summary.recent_experiments,
        top_candidates=summary.top_candidates,
        warning_items=[*summary.warning_items, *extra_warnings],
        artifacts=[_artifact_dict(artifact) for artifact in index.artifacts],
    )


def _artifact_dict(artifact: DashboardArtifact | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return artifact.model_dump(mode="json")
