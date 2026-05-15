from __future__ import annotations

from datetime import datetime
from typing import Any

from ashare_alpha.dashboard.models import DashboardArtifact, DashboardIndex, DashboardSummary


def build_dashboard_summary(index: DashboardIndex) -> DashboardSummary:
    latest_pipeline = _latest(index, "pipeline")
    latest_backtest = _latest(index, "backtest")
    latest_sweep = _latest(index, "sweep")
    latest_walkforward = _latest(index, "walkforward")
    latest_candidate_selection = _latest(index, "candidate_selection")
    top_candidates = _top_candidates(latest_candidate_selection)
    recent_experiments = _recent_experiments(index)
    warning_items = _warning_items(index)
    summary_text = _summary_text(index, latest_pipeline, latest_walkforward, top_candidates, warning_items)
    return DashboardSummary(
        generated_at=datetime.now(),
        outputs_root=index.outputs_root,
        latest_pipeline=latest_pipeline,
        latest_backtest=latest_backtest,
        latest_sweep=latest_sweep,
        latest_walkforward=latest_walkforward,
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
                warnings.append(_warning(artifact, f"{artifact.artifact_type} 存在 error 级问题。"))
        elif artifact.artifact_type == "walkforward":
            overfit_warnings = summary.get("overfit_warnings")
            if isinstance(overfit_warnings, list) and overfit_warnings:
                warnings.append(_warning(artifact, "walk-forward 存在稳定性或过拟合提示。", {"overfit_warnings": overfit_warnings}))
        elif artifact.artifact_type == "sweep":
            if _int(summary.get("failed_count")) > 0:
                warnings.append(_warning(artifact, "sweep 存在失败 variant。"))
        elif artifact.artifact_type == "pipeline":
            if artifact.status and artifact.status != "SUCCESS":
                warnings.append(_warning(artifact, f"pipeline 状态为 {artifact.status}。"))
        elif artifact.artifact_type == "unknown":
            warnings.append(_warning(artifact, "研究产物读取失败。"))
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
    top_candidates: list[dict[str, Any]],
    warning_items: list[dict[str, Any]],
) -> str:
    pipeline_text = "未发现最新 pipeline。"
    if latest_pipeline is not None:
        pipeline_text = f"最新 pipeline 状态为 {latest_pipeline.status or '未知'}。"
    wf_text = "未发现 walk-forward 稳定性结果。"
    if latest_walkforward is not None:
        warnings = latest_walkforward.summary.get("overfit_warnings")
        if isinstance(warnings, list) and warnings:
            wf_text = f"最新 walk-forward 有 {len(warnings)} 条稳定性提示，需人工复核。"
        else:
            wf_text = "最新 walk-forward 未记录主要稳定性提示。"
    risk_text = "当前汇总未发现质量、安全或审计 error。"
    if any(item.get("artifact_type") in {"quality_report", "leakage_audit", "security_scan"} for item in warning_items):
        risk_text = "当前汇总存在质量、安全或审计 error，请先复核。"
    candidate_text = "未发现建议进入下一轮验证的研究候选。"
    if any(item.get("recommendation") == "ADVANCE" for item in top_candidates):
        candidate_text = "存在建议进入下一轮验证的研究候选。"
    return (
        f"本次扫描到 {index.artifact_count} 个研究产物。{pipeline_text}"
        f"{wf_text}{risk_text}{candidate_text}"
        "该 Dashboard 只做研究汇总，不构成投资建议，不保证未来收益，也不会自动下单。"
    )


def _int(value: Any) -> int:
    if isinstance(value, bool) or value in {None, ""}:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
