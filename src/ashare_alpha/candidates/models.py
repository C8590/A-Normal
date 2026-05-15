from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CandidateSourceType = Literal["sweep", "walkforward", "experiment"]
CandidateRecommendation = Literal["ADVANCE", "REVIEW", "REJECT"]
PromotionStatus = Literal["SUCCESS", "FAILED"]


class CandidateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class CandidateSource(CandidateModel):
    source_type: CandidateSourceType
    path: str = Field(min_length=1)
    source_id: str | None = None


class CandidateRecord(CandidateModel):
    candidate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: CandidateSourceType
    source_path: str = Field(min_length=1)
    experiment_id: str | None = None
    config_dir: str | None = None
    output_dir: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CandidateScore(CandidateModel):
    candidate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    total_score: float = Field(ge=0, le=100)
    return_score: float = Field(ge=0, le=100)
    drawdown_score: float = Field(ge=0, le=100)
    stability_score: float = Field(ge=0, le=100)
    trade_activity_score: float = Field(ge=0, le=100)
    warning_penalty_score: float = Field(ge=0, le=100)
    passed_basic_filters: bool
    filter_reasons: list[str] = Field(default_factory=list)
    recommendation: CandidateRecommendation


class CandidateSelectionReport(CandidateModel):
    selection_id: str = Field(min_length=1)
    generated_at: datetime
    rules_path: str = Field(min_length=1)
    sources: list[CandidateSource] = Field(default_factory=list)
    total_candidates: int = Field(ge=0)
    advance_count: int = Field(ge=0)
    review_count: int = Field(ge=0)
    reject_count: int = Field(ge=0)
    scores: list[CandidateScore] = Field(default_factory=list)
    summary: str = Field(min_length=1)
    candidates: list[CandidateRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> CandidateSelectionReport:
        if self.total_candidates != len(self.scores):
            raise ValueError("total_candidates must equal len(scores)")
        if self.advance_count != sum(1 for score in self.scores if score.recommendation == "ADVANCE"):
            raise ValueError("advance_count does not match scores")
        if self.review_count != sum(1 for score in self.scores if score.recommendation == "REVIEW"):
            raise ValueError("review_count does not match scores")
        if self.reject_count != sum(1 for score in self.scores if score.recommendation == "REJECT"):
            raise ValueError("reject_count does not match scores")
        return self


class CandidatePromotionResult(CandidateModel):
    candidate_id: str = Field(min_length=1)
    promoted_name: str = Field(min_length=1)
    source_config_dir: str
    target_config_dir: str
    copied_files: list[str] = Field(default_factory=list)
    status: PromotionStatus
    message: str


class CandidateWeights(CandidateModel):
    return_score: float = Field(ge=0)
    drawdown_score: float = Field(ge=0)
    stability_score: float = Field(ge=0)
    trade_activity_score: float = Field(ge=0)
    warning_penalty_score: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_weight_sum(self) -> CandidateWeights:
        total = (
            self.return_score
            + self.drawdown_score
            + self.stability_score
            + self.trade_activity_score
            + self.warning_penalty_score
        )
        if abs(total - 1.0) > 0.02:
            raise ValueError("candidate scoring weights must sum close to 1.0")
        return self


class CandidateThresholds(CandidateModel):
    min_success_fold_count: int = Field(ge=0)
    min_positive_return_ratio: float = Field(ge=0, le=1)
    max_allowed_worst_drawdown: float
    min_trade_count_total: int = Field(ge=0)
    max_warning_count: int = Field(ge=0)


class CandidateScoringConfig(CandidateModel):
    return_cap: float = Field(gt=0)
    drawdown_floor: float = Field(lt=0)
    stability_std_cap: float = Field(gt=0)


class CandidatePromotionConfig(CandidateModel):
    allow_auto_promote: bool = False
    promoted_config_root: str = Field(min_length=1)
    require_manual_flag: bool = True

    @field_validator("allow_auto_promote")
    @classmethod
    def validate_no_auto_promote(cls, value: bool) -> bool:
        if value:
            raise ValueError("automatic promotion is disabled for research safety")
        return value


class CandidateRules(CandidateModel):
    selection_name: str = Field(min_length=1)
    weights: CandidateWeights
    thresholds: CandidateThresholds
    scoring: CandidateScoringConfig
    promotion: CandidatePromotionConfig
