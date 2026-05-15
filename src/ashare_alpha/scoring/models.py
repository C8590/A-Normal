from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ComponentScore:
    score: float
    reasons: list[str] = field(default_factory=list)
    risk_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarketRegimeResult:
    regime: str
    score: float
    reason: str
    stock_count: int
    pct_above_ma20: float
    pct_above_ma60: float
    avg_momentum_20d: float | None
    avg_momentum_60d: float | None


@dataclass(frozen=True)
class FundamentalScoreResult:
    score: float
    reasons: list[str] = field(default_factory=list)
    risk_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskPenaltyResult:
    risk_penalty_score: float
    risk_level: str
    risk_reasons: list[str]
