from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ashare_alpha.candidates.models import CandidateRecord, CandidateRules, CandidateScore


_SEVERE_WARNING_KEYWORDS = (
    "样本窗口过少",
    "多数窗口未取得正收益",
    "收益波动显著高于均值",
    "较大回撤窗口",
)


class CandidateScorer:
    def __init__(self, rules: CandidateRules) -> None:
        self.rules = rules

    def score(self, candidate: CandidateRecord) -> CandidateScore:
        warnings = list(candidate.warnings)
        return_score = self._return_score(candidate.metrics)
        drawdown_score = self._drawdown_score(candidate.metrics)
        stability_score = self._stability_score(candidate.metrics)
        trade_activity_score, trade_warning = self._trade_activity_score(candidate.metrics)
        if trade_warning:
            warnings.append(trade_warning)
        warning_penalty_score = self._warning_penalty_score(warnings)
        total_score = _clamp(
            return_score * self.rules.weights.return_score
            + drawdown_score * self.rules.weights.drawdown_score
            + stability_score * self.rules.weights.stability_score
            + trade_activity_score * self.rules.weights.trade_activity_score
            - warning_penalty_score * self.rules.weights.warning_penalty_score
        )
        passed_basic_filters, filter_reasons = self._basic_filters(candidate, warnings)
        recommendation = self._recommendation(total_score, passed_basic_filters)
        return CandidateScore(
            candidate_id=candidate.candidate_id,
            name=candidate.name,
            total_score=round(total_score, 4),
            return_score=round(return_score, 4),
            drawdown_score=round(drawdown_score, 4),
            stability_score=round(stability_score, 4),
            trade_activity_score=round(trade_activity_score, 4),
            warning_penalty_score=round(warning_penalty_score, 4),
            passed_basic_filters=passed_basic_filters,
            filter_reasons=filter_reasons,
            recommendation=recommendation,
        )

    def _return_score(self, metrics: dict[str, Any]) -> float:
        value = _first_number(metrics, ("mean_total_return", "total_return", "annualized_return"))
        if value is None:
            return 50.0
        cap = self.rules.scoring.return_cap
        if value <= 0:
            return _clamp(30.0 + (value / cap) * 30.0)
        return _clamp(30.0 + min(value, cap) / cap * 70.0)

    def _drawdown_score(self, metrics: dict[str, Any]) -> float:
        value = _first_number(metrics, ("worst_max_drawdown", "max_drawdown", "mean_max_drawdown"))
        if value is None:
            return 50.0
        if value > 0:
            value = -value
        floor = self.rules.scoring.drawdown_floor
        if value <= floor:
            return 0.0
        return _clamp((value - floor) / (0.0 - floor) * 100.0)

    def _stability_score(self, metrics: dict[str, Any]) -> float:
        positive_ratio = _first_number(metrics, ("positive_return_ratio",))
        std_return = _first_number(metrics, ("std_total_return",))
        success_fold_count = _first_number(metrics, ("success_fold_count",))

        components: list[float] = []
        if positive_ratio is not None:
            components.append(_clamp(positive_ratio * 100.0))
        if std_return is not None:
            std_score = (1.0 - min(abs(std_return), self.rules.scoring.stability_std_cap) / self.rules.scoring.stability_std_cap) * 100.0
            components.append(_clamp(std_score))
        if success_fold_count is not None:
            required = max(1, self.rules.thresholds.min_success_fold_count)
            components.append(_clamp(min(success_fold_count / required, 1.0) * 100.0))
        if not components:
            return 50.0
        return sum(components) / len(components)

    def _trade_activity_score(self, metrics: dict[str, Any]) -> tuple[float, str | None]:
        value = _first_number(metrics, ("trade_count", "filled_trade_count", "mean_trade_count", "total_trade_count"))
        if value is None:
            return 50.0, "缺少交易数量指标，无法充分验证交易有效性。"
        if value <= 0:
            return 50.0, "无交易结果只能说明流程稳定，无法验证交易有效性。"
        return 70.0, None

    def _warning_penalty_score(self, warnings: list[str]) -> float:
        if not warnings:
            return 0.0
        penalty = min(len(warnings) * 12.0, 60.0)
        severe_count = sum(1 for warning in warnings if any(keyword in warning for keyword in _SEVERE_WARNING_KEYWORDS))
        penalty += severe_count * 15.0
        return _clamp(penalty)

    def _basic_filters(self, candidate: CandidateRecord, warnings: list[str]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        metrics = candidate.metrics
        if not metrics:
            reasons.append("候选指标为空，无法进行有效评估。")
        success_fold_count = _first_number(metrics, ("success_fold_count",))
        if candidate.source_type == "walkforward" and success_fold_count is not None:
            if success_fold_count < self.rules.thresholds.min_success_fold_count:
                reasons.append(
                    f"成功 walk-forward 窗口数 {success_fold_count:g} 低于阈值 "
                    f"{self.rules.thresholds.min_success_fold_count}。"
                )
        positive_ratio = _first_number(metrics, ("positive_return_ratio",))
        if positive_ratio is not None and positive_ratio < self.rules.thresholds.min_positive_return_ratio:
            reasons.append(
                f"正收益窗口比例 {positive_ratio:.2f} 低于阈值 "
                f"{self.rules.thresholds.min_positive_return_ratio:.2f}。"
            )
        worst_drawdown = _first_number(metrics, ("worst_max_drawdown",))
        if worst_drawdown is not None:
            normalized_drawdown = -worst_drawdown if worst_drawdown > 0 else worst_drawdown
            if normalized_drawdown < self.rules.thresholds.max_allowed_worst_drawdown:
                reasons.append(
                    f"最差最大回撤 {normalized_drawdown:.4f} 低于允许阈值 "
                    f"{self.rules.thresholds.max_allowed_worst_drawdown:.4f}。"
                )
        if len(warnings) > self.rules.thresholds.max_warning_count:
            reasons.append(f"风险提示数量 {len(warnings)} 超过阈值 {self.rules.thresholds.max_warning_count}。")
        return not reasons, reasons

    @staticmethod
    def _recommendation(total_score: float, passed_basic_filters: bool) -> str:
        if total_score >= 75.0 and passed_basic_filters:
            return "ADVANCE"
        if total_score >= 55.0:
            return "REVIEW"
        return "REJECT"


def load_candidate_rules(path: Path) -> CandidateRules:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"candidate rules must be a mapping: {path}")
    return CandidateRules.model_validate(payload)


def _first_number(metrics: dict[str, Any], names: tuple[str, ...]) -> float | None:
    for name in names:
        value = _number(metrics.get(name))
        if value is not None:
            return value
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))
