from __future__ import annotations

from ashare_alpha.config import ProjectConfig
from ashare_alpha.events import EventDailyRecord
from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.scoring.components import clamp_score
from ashare_alpha.scoring.models import FundamentalScoreResult, RiskPenaltyResult
from ashare_alpha.universe import UniverseDailyRecord


def calculate_risk_penalty(
    config: ProjectConfig,
    universe: UniverseDailyRecord | None,
    factor: FactorDailyRecord | None,
    event: EventDailyRecord | None,
    fundamental: FundamentalScoreResult,
) -> RiskPenaltyResult:
    score = 0.0
    reasons: list[str] = []
    risk_config = config.scoring.risk_penalty

    if universe is not None:
        universe_penalty = min(40.0, universe.risk_score * 0.4)
        if universe_penalty > 0:
            score += universe_penalty
            reasons.append(f"股票池风险分贡献 {universe_penalty:.1f}")
        if universe.liquidity_score < 60:
            score += risk_config["low_liquidity"]
            reasons.append("流动性评分偏低")

    if event is not None:
        if event.event_risk_score >= config.scoring.risk_level_thresholds.high:
            score += 40
            reasons.append("公告事件风险分较高")
        elif event.event_risk_score >= config.scoring.risk_level_thresholds.medium:
            score += 25
            reasons.append("公告事件风险分偏高")

    if factor is not None:
        if factor.volatility_20d is not None and factor.volatility_20d > 0.05:
            score += risk_config["high_volatility"]
            reasons.append("20日波动率较高")
        if factor.max_drawdown_20d is not None and factor.max_drawdown_20d <= -0.15:
            score += risk_config["high_volatility"]
            reasons.append("20日最大回撤较大")
        if factor.limit_down_recent_count > 0:
            score += risk_config["recent_limit_down"]
            reasons.append("近窗口出现跌停")

    financial_penalty = risk_config["high_financial_risk"]
    for reason in fundamental.risk_reasons:
        if reason in {"资产负债率较高", "商誉占净资产比例较高", "净利润同比为负", "经营现金流质量较差"}:
            score += financial_penalty
            reasons.append(reason)

    penalty_score = clamp_score(score)
    thresholds = config.scoring.risk_level_thresholds
    if penalty_score >= thresholds.high:
        risk_level = "high"
    elif penalty_score >= thresholds.medium:
        risk_level = "medium"
    else:
        risk_level = "low"
    return RiskPenaltyResult(risk_penalty_score=penalty_score, risk_level=risk_level, risk_reasons=_dedupe(reasons))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result
