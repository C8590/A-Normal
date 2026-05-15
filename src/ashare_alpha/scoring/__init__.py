from __future__ import annotations

from ashare_alpha.scoring.components import event_component_score, score_trend_momentum, score_volatility_control
from ashare_alpha.scoring.fundamental import latest_financial_by_code, score_fundamental_quality
from ashare_alpha.scoring.industry import compute_industry_strength_scores
from ashare_alpha.scoring.market import compute_market_regime
from ashare_alpha.scoring.models import ComponentScore, FundamentalScoreResult, MarketRegimeResult, RiskPenaltyResult
from ashare_alpha.scoring.risk_penalty import calculate_risk_penalty
from ashare_alpha.scoring.stock_score import calculate_raw_score

__all__ = [
    "ComponentScore",
    "FundamentalScoreResult",
    "MarketRegimeResult",
    "RiskPenaltyResult",
    "calculate_raw_score",
    "calculate_risk_penalty",
    "compute_industry_strength_scores",
    "compute_market_regime",
    "event_component_score",
    "latest_financial_by_code",
    "score_fundamental_quality",
    "score_trend_momentum",
    "score_volatility_control",
]
