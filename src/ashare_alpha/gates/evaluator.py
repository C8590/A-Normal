from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha.gates.loader import ResearchArtifactLoader
from ashare_alpha.gates.models import (
    LoadedArtifact,
    ResearchGateArtifactSummary,
    ResearchGateIssue,
    ResearchGateReport,
    ResearchQualityGateConfig,
    decision_from_issues,
)


class ResearchGateEvaluator:
    def __init__(
        self,
        gate_config: ResearchQualityGateConfig,
        artifact_paths: list[Path],
        gate_config_path: Path,
        loader: ResearchArtifactLoader | None = None,
    ) -> None:
        self.gate_config = gate_config
        self.artifact_paths = [Path(path) for path in artifact_paths]
        self.gate_config_path = Path(gate_config_path)
        self.loader = loader or ResearchArtifactLoader()

    def evaluate(self) -> ResearchGateReport:
        loaded_artifacts = self.loader.load_many(self.artifact_paths)
        artifact_summaries: list[ResearchGateArtifactSummary] = []
        issues: list[ResearchGateIssue] = []
        for artifact in loaded_artifacts:
            artifact_issues = self._evaluate_artifact(artifact)
            issues.extend(artifact_issues)
            artifact_summaries.append(
                ResearchGateArtifactSummary(
                    artifact_type=artifact.artifact_type,
                    path=artifact.path,
                    status=_status(artifact),
                    metrics=_metrics(artifact),
                    issue_count=len(artifact_issues),
                    decision=decision_from_issues(artifact_issues),
                )
            )

        blocker_count = sum(1 for issue in issues if issue.severity == "BLOCKER")
        warning_count = sum(1 for issue in issues if issue.severity == "WARNING")
        info_count = sum(1 for issue in issues if issue.severity == "INFO")
        overall_decision = "BLOCK" if blocker_count > 0 else "WARN" if warning_count > 0 else "PASS"
        return ResearchGateReport(
            report_id=f"research_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            gate_config_path=str(self.gate_config_path),
            sources=[str(path) for path in self.artifact_paths],
            overall_decision=overall_decision,
            pass_count=sum(1 for item in artifact_summaries if item.decision == "PASS"),
            warn_count=sum(1 for item in artifact_summaries if item.decision == "WARN"),
            block_count=sum(1 for item in artifact_summaries if item.decision == "BLOCK"),
            issue_count=len(issues),
            blocker_count=blocker_count,
            warning_count=warning_count,
            info_count=info_count,
            artifact_summaries=artifact_summaries,
            issues=issues,
            summary=_summary(overall_decision),
        )

    def _evaluate_artifact(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        if artifact.data.get("_loader_error"):
            return [
                self._issue(
                    "BLOCKER",
                    artifact,
                    "artifact_load_failed",
                    f"研究产物无法读取：{artifact.data['_loader_error']}",
                    "修复或重新生成该 JSON 产物后再评估质量门禁。",
                )
            ]
        evaluator = {
            "data_quality": self._evaluate_data_quality,
            "leakage_audit": self._evaluate_leakage_audit,
            "security": self._evaluate_security,
            "pipeline": self._evaluate_pipeline,
            "backtest": self._evaluate_backtest,
            "sweep": self._evaluate_sweep,
            "walkforward": self._evaluate_walkforward,
            "candidate_selection": self._evaluate_candidate_selection,
            "adjusted_research": self._evaluate_adjusted_research,
        }.get(artifact.artifact_type)
        if evaluator is None:
            return [
                self._issue(
                    "WARNING",
                    artifact,
                    "unknown_artifact_type",
                    "无法识别该研究产物类型，未应用专门门禁规则。",
                    "使用支持的 JSON 文件名，或人工复核该产物。",
                )
            ]
        return evaluator(artifact)

    def _evaluate_data_quality(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.data_quality
        issues: list[ResearchGateIssue] = []
        error_count = _int(artifact.data.get("error_count"))
        warning_count = _int(artifact.data.get("warning_count"))
        if artifact.data.get("passed") is False and error_count > 0 and config.block_on_error:
            issues.append(self._issue("BLOCKER", artifact, "data_quality_error", "数据质量存在 error 级问题，不应进入候选。", "先修复数据质量 error。"))
        if warning_count > config.max_warning_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "data_quality_warning_count",
                    f"数据质量 warning 数量 {warning_count} 超过阈值 {config.max_warning_count}。",
                    "人工复核 warning 并降低缺失、异常或覆盖不足问题。",
                )
            )
        return issues

    def _evaluate_leakage_audit(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.leakage_audit
        issues: list[ResearchGateIssue] = []
        error_count = _int(artifact.data.get("error_count"))
        warning_count = _int(artifact.data.get("warning_count"))
        if error_count > 0 and config.block_on_error:
            issues.append(self._issue("BLOCKER", artifact, "leakage_audit_error", "泄漏审计存在 error 级问题。", "修复 point-in-time 数据泄漏后再继续研究。"))
        if warning_count > config.max_warning_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "leakage_audit_warning_count",
                    f"泄漏审计 warning 数量 {warning_count} 超过阈值 {config.max_warning_count}。",
                    "人工复核泄漏审计 warning。",
                )
            )
        return issues

    def _evaluate_security(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.security
        issues: list[ResearchGateIssue] = []
        error_count = _int(artifact.data.get("error_count"))
        warning_count = _int(artifact.data.get("warning_count"))
        if error_count > 0 and config.block_on_error:
            issues.append(self._issue("BLOCKER", artifact, "security_error", "安全扫描存在 error 级问题，pipeline 应直接 failed。", "修复安全配置、秘密或实盘开关问题。"))
        if warning_count > config.max_warning_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "security_warning_count",
                    f"安全扫描 warning 数量 {warning_count} 超过阈值 {config.max_warning_count}。",
                    "人工复核安全 warning。",
                )
            )
        return issues

    def _evaluate_pipeline(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.pipeline
        issues: list[ResearchGateIssue] = []
        status = str(artifact.data.get("status") or "")
        allowed_universe = _int(artifact.data.get("allowed_universe_count"))
        high_risk = _int(artifact.data.get("high_risk_count"))
        if status not in config.allowed_status:
            issues.append(self._issue("BLOCKER", artifact, "pipeline_status", f"pipeline status={status or 'unknown'} 不在允许范围。", "先让 pipeline 正常完成。"))
        if allowed_universe < config.min_allowed_universe_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "pipeline_low_universe",
                    f"可研究股票池数量 {allowed_universe} 低于阈值 {config.min_allowed_universe_count}。",
                    "复核 universe 过滤和数据覆盖，避免样本过窄。",
                )
            )
        if config.max_high_risk_count is not None and high_risk > config.max_high_risk_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "pipeline_high_risk_count",
                    f"高风险股票数量 {high_risk} 超过阈值 {config.max_high_risk_count}。",
                    "复核风险事件和过滤规则。",
                )
            )
        return issues

    def _evaluate_backtest(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.backtest
        issues: list[ResearchGateIssue] = []
        filled_trades = _int(artifact.data.get("filled_trade_count", artifact.data.get("trade_count")))
        max_drawdown = _float(artifact.data.get("max_drawdown"))
        sharpe = _float(artifact.data.get("sharpe"))
        if filled_trades < config.min_filled_trade_count and config.require_trades_for_effectiveness_claim:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "backtest_low_trade_count",
                    "回测无成交或成交不足，不能用于验证策略有效性。",
                    "补充样本、放宽研究阈值或仅将结果标记为无交易观察。",
                )
            )
        if max_drawdown is not None and max_drawdown < config.max_drawdown_block_threshold:
            issues.append(
                self._issue(
                    "BLOCKER",
                    artifact,
                    "backtest_drawdown_block",
                    f"最大回撤 {max_drawdown:.4f} 低于阻断阈值 {config.max_drawdown_block_threshold:.4f}。",
                    "降低回撤风险后再考虑晋级或发布。",
                )
            )
        if sharpe is not None and sharpe < config.min_sharpe_warn_threshold:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "backtest_low_sharpe",
                    f"Sharpe {sharpe:.4f} 低于 warning 阈值 {config.min_sharpe_warn_threshold:.4f}。",
                    "人工复核收益稳定性，避免宣称策略有效。",
                )
            )
        return issues

    def _evaluate_sweep(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.sweep
        issues: list[ResearchGateIssue] = []
        success_count = _int(artifact.data.get("success_count"))
        failed_count = _int(artifact.data.get("failed_count"))
        total_variants = _int(artifact.data.get("total_variants"))
        if success_count < config.min_success_count:
            issues.append(self._issue("BLOCKER", artifact, "sweep_low_success_count", "sweep 成功变体数量不足。", "先修复 sweep 配置或失败变体。"))
        if total_variants > 0 and failed_count / total_variants > config.max_failed_ratio:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "sweep_failed_ratio",
                    f"sweep 失败比例 {failed_count / total_variants:.2f} 超过阈值 {config.max_failed_ratio:.2f}。",
                    "人工复核失败变体，避免选择不稳定配置。",
                )
            )
        return issues

    def _evaluate_walkforward(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.walkforward
        issues: list[ResearchGateIssue] = []
        success_count = _int(artifact.data.get("success_count"))
        stability = artifact.data.get("stability_metrics") if isinstance(artifact.data.get("stability_metrics"), dict) else {}
        positive_ratio = _float(stability.get("positive_return_ratio"))
        worst_drawdown = _float(stability.get("worst_max_drawdown"))
        overfit_warnings = artifact.data.get("overfit_warnings")
        folds = artifact.data.get("folds") if isinstance(artifact.data.get("folds"), list) else []
        trade_counts = [_int(fold.get("metrics", {}).get("trade_count", fold.get("metrics", {}).get("filled_trade_count"))) for fold in folds if isinstance(fold, dict)]
        if success_count < config.min_success_fold_count:
            issues.append(self._issue("BLOCKER", artifact, "walkforward_low_success_count", "walk-forward 成功窗口数量不足，不允许晋级配置。", "补足样本外窗口后再评估。"))
        if positive_ratio is not None and positive_ratio < config.min_positive_return_ratio:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "walkforward_low_positive_return_ratio",
                    f"样本外正收益窗口比例 {positive_ratio:.2f} 低于阈值 {config.min_positive_return_ratio:.2f}。",
                    "人工复核样本外稳定性。",
                )
            )
        if worst_drawdown is not None and worst_drawdown < config.max_worst_drawdown:
            issues.append(
                self._issue(
                    "BLOCKER",
                    artifact,
                    "walkforward_worst_drawdown",
                    f"样本外最差回撤 {worst_drawdown:.4f} 低于阈值 {config.max_worst_drawdown:.4f}。",
                    "降低样本外回撤风险后再晋级。",
                )
            )
        if trade_counts and all(value == 0 for value in trade_counts) and config.block_if_all_no_trade:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "walkforward_all_no_trade",
                    "所有 walk-forward 窗口均无交易，不能证明配置有效。",
                    "人工复核阈值和样本覆盖。",
                )
            )
        if isinstance(overfit_warnings, list) and overfit_warnings:
            issues.append(self._issue("WARNING", artifact, "walkforward_overfit_warnings", "walk-forward 存在稳定性或过拟合提示。", "逐项复核 overfit_warnings。"))
        return issues

    def _evaluate_candidate_selection(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.candidate_selection
        issues: list[ResearchGateIssue] = []
        total_candidates = _int(artifact.data.get("total_candidates"))
        advance_count = _int(artifact.data.get("advance_count"))
        scores = artifact.data.get("scores") if isinstance(artifact.data.get("scores"), list) else []
        if total_candidates == 0 and config.block_if_no_candidates:
            issues.append(self._issue("BLOCKER", artifact, "candidate_no_candidates", "候选集为空，不允许进入候选晋级。", "先生成有效候选。"))
        if advance_count < config.min_advance_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "candidate_low_advance_count",
                    f"ADVANCE 候选数量 {advance_count} 低于阈值 {config.min_advance_count}。",
                    "人工复核候选评分和样本外稳定性。",
                )
            )
        if scores and all(isinstance(score, dict) and score.get("recommendation") == "REJECT" for score in scores):
            issues.append(self._issue("WARNING", artifact, "candidate_all_reject", "所有候选均为 REJECT。", "不建议 promote，需回到研究配置阶段。"))
        return issues

    def _evaluate_adjusted_research(self, artifact: LoadedArtifact) -> list[ResearchGateIssue]:
        config = self.gate_config.adjusted_research
        issues: list[ResearchGateIssue] = []
        status = str(artifact.data.get("status") or "")
        warning_items = artifact.data.get("warning_items") if isinstance(artifact.data.get("warning_items"), list) else []
        factor_comparisons = artifact.data.get("factor_comparisons") if isinstance(artifact.data.get("factor_comparisons"), list) else []
        backtest_comparisons = artifact.data.get("backtest_comparisons") if isinstance(artifact.data.get("backtest_comparisons"), list) else []
        if status == "FAILED" and config.block_on_failed:
            issues.append(self._issue("BLOCKER", artifact, "adjusted_research_failed", "复权研究报告 FAILED，不允许得出 adjusted 结论。", "修复失败步骤后重新生成报告。"))
        if status == "PARTIAL" and config.warn_on_partial:
            severity = "WARNING" if config.allow_partial else "BLOCKER"
            issues.append(self._issue(severity, artifact, "adjusted_research_partial", "复权研究报告为 PARTIAL，需要人工复核。", "查看 warning_items 和 Markdown 报告。"))
        if len(warning_items) > config.max_warning_count:
            issues.append(
                self._issue(
                    "WARNING",
                    artifact,
                    "adjusted_research_warning_count",
                    f"复权研究 warning 数量 {len(warning_items)} 超过阈值 {config.max_warning_count}。",
                    "提升复权覆盖后再得出结论。",
                )
            )
        if len(factor_comparisons) < config.min_factor_comparison_count:
            issues.append(self._issue("WARNING", artifact, "adjusted_research_low_factor_comparisons", "factor 复权比较数量不足。", "补足 raw/qfq/hfq 因子比较。"))
        if len(backtest_comparisons) < config.min_backtest_comparison_count:
            issues.append(self._issue("WARNING", artifact, "adjusted_research_low_backtest_comparisons", "backtest 复权比较数量不足。", "补足 raw/qfq/hfq 回测比较。"))
        return issues

    def _issue(
        self,
        severity: str,
        artifact: LoadedArtifact,
        issue_type: str,
        message: str,
        recommendation: str,
    ) -> ResearchGateIssue:
        return ResearchGateIssue(
            severity=severity,
            gate_name=self.gate_config.gate_name,
            artifact_type=artifact.artifact_type,
            artifact_path=artifact.path,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
        )


def _status(artifact: LoadedArtifact) -> str | None:
    if artifact.data.get("_loader_error"):
        return "FAILED"
    if "status" in artifact.data:
        return str(artifact.data.get("status"))
    if "passed" in artifact.data:
        return "SUCCESS" if artifact.data.get("passed") is True else "FAILED"
    return None


def _metrics(artifact: LoadedArtifact) -> dict[str, Any]:
    keys = (
        "passed",
        "total_issues",
        "error_count",
        "warning_count",
        "total_stocks",
        "allowed_universe_count",
        "high_risk_count",
        "total_return",
        "max_drawdown",
        "sharpe",
        "trade_count",
        "filled_trade_count",
        "total_variants",
        "success_count",
        "failed_count",
        "fold_count",
        "advance_count",
        "total_candidates",
    )
    result = {key: artifact.data.get(key) for key in keys if key in artifact.data}
    if artifact.artifact_type == "adjusted_research":
        result["factor_comparison_count"] = len(artifact.data.get("factor_comparisons", [])) if isinstance(artifact.data.get("factor_comparisons"), list) else 0
        result["backtest_comparison_count"] = len(artifact.data.get("backtest_comparisons", [])) if isinstance(artifact.data.get("backtest_comparisons"), list) else 0
        result["warning_count"] = len(artifact.data.get("warning_items", [])) if isinstance(artifact.data.get("warning_items"), list) else 0
    if artifact.artifact_type == "walkforward" and isinstance(artifact.data.get("stability_metrics"), dict):
        result.update({f"stability_{key}": value for key, value in artifact.data["stability_metrics"].items()})
    return result


def _summary(decision: str) -> str:
    if decision == "BLOCK":
        return "研究质量门禁结果为 BLOCK：不建议晋级或发布，不建议 promote。该结论仅用于研究质量控制，不构成投资建议，不保证未来收益。"
    if decision == "WARN":
        return "研究质量门禁结果为 WARN：需要人工复核后再决定是否进入下一轮研究。该结论仅用于研究质量控制，不构成投资建议，不保证未来收益。"
    return "研究质量门禁结果为 PASS：仅代表输入产物通过本轮研究质量门禁，不代表收益保证，不构成投资建议。"


def _int(value: Any) -> int:
    if isinstance(value, bool) or value in {None, ""}:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float | None:
    if isinstance(value, bool) or value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
