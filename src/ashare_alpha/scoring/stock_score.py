from __future__ import annotations

from ashare_alpha.config import ProjectConfig
from ashare_alpha.scoring.components import clamp_score


def calculate_raw_score(
    config: ProjectConfig,
    market_regime_score: float,
    industry_strength_score: float,
    trend_momentum_score: float,
    fundamental_quality_score: float,
    liquidity_score: float,
    event_component_score: float,
    volatility_control_score: float,
) -> float:
    weights = config.scoring.weights
    return clamp_score(
        market_regime_score * weights["market_regime"]
        + industry_strength_score * weights["industry_strength"]
        + trend_momentum_score * weights["trend_momentum"]
        + fundamental_quality_score * weights["fundamental_quality"]
        + liquidity_score * weights["liquidity"]
        + event_component_score * weights["event"]
        + volatility_control_score * weights["volatility_control"]
    )
