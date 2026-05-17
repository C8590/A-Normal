from __future__ import annotations

from datetime import datetime
from typing import Any

from ashare_alpha.dashboard.models import DashboardArtifact, DashboardIndex, DashboardSummary


def build_dashboard_summary(index: DashboardIndex) -> DashboardSummary:
    latest_pipeline = _latest(index, "pipeline")
    latest_backtest = _latest(index, "backtest")
    latest_sweep = _latest(index, "sweep")
    latest_walkforward = _latest(index, "walkforward")
    latest_adjusted_research = _latest(index, "adjusted_research")
    latest_research_gate = _latest(index, "research_gate")
    latest_candidate_selection = _latest(index, "candidate_selection")
    top_candidates = _top_candidates(latest_candidate_selection)
    recent_experiments = _recent_experiments(index)
    warning_items = _warning_items(index)
    summary_text = _summary_text(
        index,
        latest_pipeline,
        latest_walkforward,
        latest_adjusted_research,
        latest_research_gate,
        top_candidates,
        warning_items,
    )
    return DashboardSummary(
        generated_at=datetime.now(),
        outputs_root=index.outputs_root,
        latest_pipeline=latest_pipeline,
        latest_backtest=latest_backtest,
        latest_sweep=latest_sweep,
        latest_walkforward=latest_walkforward,
        latest_adjusted_research=latest_adjusted_research,
        latest_research_gate=latest_research_gate,
        latest_candidate_selection=latest_candidate_selection,
        top_candidates=top_candidates,
        recent_experiments=recent_experiments,
        warning_items=warning_items,
        summary_text=summary_text,
    )


def _latest(index: DashboardIndex, artifact_type: str) -> DashboardArtifact | None:
    return next((artifact for artifact in index.artifacts if artifact.artifact_type == artifact_type), None)


def _top_candidates(artifact: DashboardArtifact | None) -> list[dict[str, Any]]:
    if artifact is None:
        return []
    scores = artifact.summary.get("top_scores")
    if not isinstance(scores, list):
        return []
    result: list[dict[str, Any]] = []
    for score in scores[:10]:
        if isinstance(score, dict):
            result.append(
                {
                    "candidate_id": score.get("candidate_id"),
                    "name": score.get("name"),
                    "total_score": score.get("total_score"),
                    "recommendation": score.get("recommendation"),
                    "filter_reasons": score.get("filter_reasons", []),
                }
            )
    return result


def _recent_experiments(index: DashboardIndex) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in index.artifacts:
        if artifact.artifact_type != "experiment":
            continue
        rows.append(
            {
                "experiment_id": artifact.summary.get("experiment_id"),
                "command": artifact.summary.get("command"),
                "status": artifact.status,
                "data_source": artifact.summary.get("data_source"),
                "data_version": artifact.summary.get("data_version"),
                "tags": artifact.summary.get("tags", []),
                "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
                "path": artifact.path,
            }
        )
        if len(rows) >= 20:
            break
    return rows


def _warning_items(index: DashboardIndex) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for artifact in index.artifacts:
        summary = artifact.summary
        if artifact.artifact_type in {"quality_report", "leakage_audit", "security_scan"}:
            if _int(summary.get("error_count")) > 0:
                warnings.append(_warning(artifact, f"{artifact.artifact_type} has error-level issues."))
        elif artifact.artifact_type == "walkforward":
            overfit_warnings = summary.get("overfit_warnings")
            if isinstance(overfit_warnings, list) and overfit_warnings:
                warnings.append(_warning(artifact, "walk-forward has stability or overfit warnings.", {"overfit_warnings": overfit_warnings}))
        elif artifact.artifact_type == "sweep":
            if _int(summary.get("failed_count")) > 0:
                warnings.append(_warning(artifact, "sweep has failed variants."))
        elif artifact.artifact_type == "pipeline":
            if artifact.status and artifact.status != "SUCCESS":
                warnings.append(_warning(artifact, f"pipeline status is {artifact.status}."))
        elif artifact.artifact_type == "adjusted_research":
            warning_items = summary.get("warning_items")
            warning_count = _int(summary.get("warning_count"))
            if artifact.status and artifact.status != "SUCCESS":
                warnings.append(_warning(artifact, f"adjusted_research status is {artifact.status}.", {"warning_items": warning_items or []}))
            elif warning_count > 0:
                warnings.append(_warning(artifact, "adjusted_research has research warnings.", {"warning_items": warning_items or []}))
        elif artifact.artifact_type == "research_gate":
            if artifact.status == "BLOCK":
                warnings.append(_warning(artifact, "research quality gate decision is BLOCK."))
            elif artifact.status == "WARN":
                warnings.append(_warning(artifact, "research quality gate decision is WARN."))
        elif artifact.artifact_type == "unknown":
            warnings.append(_warning(artifact, "research artifact could not be read."))
    return warnings


def _warning(artifact: DashboardArtifact, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "name": artifact.name,
        "path": artifact.path,
        "message": message,
    }
    if extra:
        row.update(extra)
    return row


def _summary_text(
    index: DashboardIndex,
    latest_pipeline: DashboardArtifact | None,
    latest_walkforward: DashboardArtifact | None,
    latest_adjusted_research: DashboardArtifact | None,
    latest_research_gate: DashboardArtifact | None,
    top_candidates: list[dict[str, Any]],
    warning_items: list[dict[str, Any]],
) -> str:
    pipeline_text = "No latest pipeline was found."
    if latest_pipeline is not None:
        pipeline_text = f"Latest pipeline status is {latest_pipeline.status or 'unknown'}."
    wf_text = "No walk-forward stability result was found."
    if latest_walkforward is not None:
        warnings = latest_walkforward.summary.get("overfit_warnings")
        if isinstance(warnings, list) and warnings:
            wf_text = f"Latest walk-forward has {len(warnings)} stability warnings."
        else:
            wf_text = "Latest walk-forward has no major stability warnings."
    adjusted_text = "No adjusted research comparison has been scanned."
    if latest_adjusted_research is not None:
        adjusted_text = (
            f"Latest adjusted research status is {latest_adjusted_research.status or 'unknown'} "
            f"with {_int(latest_adjusted_research.summary.get('warning_count'))} warning items."
        )
    gate_text = "No research quality gate report has been scanned."
    if latest_research_gate is not None:
        gate_text = (
            f"Latest research gate decision is {latest_research_gate.status or 'unknown'} "
            f"with {_int(latest_research_gate.summary.get('blocker_count'))} blockers and "
            f"{_int(latest_research_gate.summary.get('warning_count'))} warnings."
        )
    risk_text = "No quality, security, or audit errors were found in this summary."
    if any(item.get("artifact_type") in {"quality_report", "leakage_audit", "security_scan"} for item in warning_items):
        risk_text = "Quality, security, or audit errors exist and should be reviewed first."
    candidate_text = "No research candidate was marked for the next validation round."
    if any(item.get("recommendation") == "ADVANCE" for item in top_candidates):
        candidate_text = "Some research candidates are marked for the next validation round."
    return (
        f"Scanned {index.artifact_count} research artifacts. "
        f"{pipeline_text} {wf_text} {adjusted_text} {gate_text} {risk_text} {candidate_text} "
        "Dashboard is for research summary only; 不构成投资建议; no future return is guaranteed, and no automatic orders are placed."
    )


def _int(value: Any) -> int:
    if isinstance(value, bool) or value in {None, ""}:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
