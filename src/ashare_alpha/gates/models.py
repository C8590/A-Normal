from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


GateSeverity = Literal["INFO", "WARNING", "BLOCKER"]
GateDecision = Literal["PASS", "WARN", "BLOCK"]


class GateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class DataQualityGateConfig(GateModel):
    block_on_error: bool = True
    max_warning_count: int = Field(default=50, ge=0)


class LeakageAuditGateConfig(GateModel):
    block_on_error: bool = True
    max_warning_count: int = Field(default=20, ge=0)


class SecurityGateConfig(GateModel):
    block_on_error: bool = True
    max_warning_count: int = Field(default=0, ge=0)


class PipelineGateConfig(GateModel):
    allowed_status: list[str] = Field(default_factory=lambda: ["SUCCESS"], min_length=1)
    min_allowed_universe_count: int = Field(default=1, ge=0)
    max_high_risk_count: int | None = Field(default=None, ge=0)


class BacktestGateConfig(GateModel):
    require_trades_for_effectiveness_claim: bool = True
    min_filled_trade_count: int = Field(default=1, ge=0)
    max_drawdown_block_threshold: float = Field(default=-0.30, le=0)
    min_sharpe_warn_threshold: float = 0.0


class SweepGateConfig(GateModel):
    min_success_count: int = Field(default=1, ge=0)
    max_failed_ratio: float = Field(default=0.5, ge=0, le=1)


class WalkForwardGateConfig(GateModel):
    min_success_fold_count: int = Field(default=3, ge=0)
    min_positive_return_ratio: float = Field(default=0.5, ge=0, le=1)
    max_worst_drawdown: float = Field(default=-0.20, le=0)
    block_if_all_no_trade: bool = True


class CandidateSelectionGateConfig(GateModel):
    min_advance_count: int = Field(default=1, ge=0)
    block_if_no_candidates: bool = True


class AdjustedResearchGateConfig(GateModel):
    allow_partial: bool = True
    block_on_failed: bool = True
    warn_on_partial: bool = True
    max_warning_count: int = Field(default=20, ge=0)
    min_factor_comparison_count: int = Field(default=1, ge=0)
    min_backtest_comparison_count: int = Field(default=1, ge=0)


class PromotionGateConfig(GateModel):
    block_promote_on_gate_block: bool = True


class ResearchQualityGateConfig(GateModel):
    gate_name: str = Field(min_length=1)
    data_quality: DataQualityGateConfig = Field(default_factory=DataQualityGateConfig)
    leakage_audit: LeakageAuditGateConfig = Field(default_factory=LeakageAuditGateConfig)
    security: SecurityGateConfig = Field(default_factory=SecurityGateConfig)
    pipeline: PipelineGateConfig = Field(default_factory=PipelineGateConfig)
    backtest: BacktestGateConfig = Field(default_factory=BacktestGateConfig)
    sweep: SweepGateConfig = Field(default_factory=SweepGateConfig)
    walkforward: WalkForwardGateConfig = Field(default_factory=WalkForwardGateConfig)
    candidate_selection: CandidateSelectionGateConfig = Field(default_factory=CandidateSelectionGateConfig)
    adjusted_research: AdjustedResearchGateConfig = Field(default_factory=AdjustedResearchGateConfig)
    promotion: PromotionGateConfig = Field(default_factory=PromotionGateConfig)


class LoadedArtifact(GateModel):
    artifact_type: str = Field(min_length=1)
    path: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class ResearchGateIssue(GateModel):
    severity: GateSeverity
    gate_name: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    artifact_path: str | None = None
    issue_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ResearchGateArtifactSummary(GateModel):
    artifact_type: str = Field(min_length=1)
    path: str = Field(min_length=1)
    status: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    issue_count: int = Field(ge=0)
    decision: GateDecision


class ResearchGateReport(GateModel):
    report_id: str = Field(min_length=1)
    generated_at: datetime
    gate_config_path: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)
    overall_decision: GateDecision
    pass_count: int = Field(ge=0)
    warn_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    artifact_summaries: list[ResearchGateArtifactSummary] = Field(default_factory=list)
    issues: list[ResearchGateIssue] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_decision_counts(self) -> ResearchGateReport:
        if self.issue_count != len(self.issues):
            raise ValueError("issue_count must equal len(issues)")
        if self.blocker_count != sum(1 for issue in self.issues if issue.severity == "BLOCKER"):
            raise ValueError("blocker_count does not match issues")
        if self.warning_count != sum(1 for issue in self.issues if issue.severity == "WARNING"):
            raise ValueError("warning_count does not match issues")
        if self.info_count != sum(1 for issue in self.issues if issue.severity == "INFO"):
            raise ValueError("info_count does not match issues")
        if self.pass_count != sum(1 for item in self.artifact_summaries if item.decision == "PASS"):
            raise ValueError("pass_count does not match artifact summaries")
        if self.warn_count != sum(1 for item in self.artifact_summaries if item.decision == "WARN"):
            raise ValueError("warn_count does not match artifact summaries")
        if self.block_count != sum(1 for item in self.artifact_summaries if item.decision == "BLOCK"):
            raise ValueError("block_count does not match artifact summaries")
        expected: GateDecision = "PASS"
        if self.blocker_count > 0:
            expected = "BLOCK"
        elif self.warning_count > 0:
            expected = "WARN"
        if self.overall_decision != expected:
            raise ValueError("overall_decision must match issue severity counts")
        return self


def decision_from_issues(issues: list[ResearchGateIssue]) -> GateDecision:
    if any(issue.severity == "BLOCKER" for issue in issues):
        return "BLOCK"
    if any(issue.severity == "WARNING" for issue in issues):
        return "WARN"
    return "PASS"
