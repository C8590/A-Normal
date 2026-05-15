from __future__ import annotations

from dataclasses import dataclass, field

from ashare_alpha.config import ProjectConfig


@dataclass(frozen=True)
class BuyCandidate:
    ts_code: str
    stock_score: float
    latest_close: float | None


@dataclass(frozen=True)
class PositionSizingResult:
    signal: str
    target_weight: float
    target_shares: int
    estimated_position_value: float
    extra_buy_reasons: list[str] = field(default_factory=list)
    extra_risk_reasons: list[str] = field(default_factory=list)
    reason_suffixes: list[str] = field(default_factory=list)


def size_buy_candidates(
    candidates: list[BuyCandidate],
    config: ProjectConfig,
) -> dict[str, PositionSizingResult]:
    max_positions = config.backtest.max_positions
    results: dict[str, PositionSizingResult] = {}
    for index, candidate in enumerate(candidates):
        if index >= max_positions:
            results[candidate.ts_code] = _watch("超过最大持仓数量限制")
            continue
        results[candidate.ts_code] = _size_one_candidate(candidate, config)
    return results


def _size_one_candidate(candidate: BuyCandidate, config: ProjectConfig) -> PositionSizingResult:
    if candidate.latest_close is None or candidate.latest_close <= 0:
        return _watch("最新收盘价缺失或无效，不能计算研究仓位")

    target_weight = min(_target_weight(candidate.stock_score, config), config.backtest.max_position_weight)
    raw_position_value = config.backtest.initial_cash * target_weight
    lot_size = config.trading_rules.lot_size
    target_shares = int(raw_position_value / candidate.latest_close / lot_size) * lot_size
    estimated_value = target_shares * candidate.latest_close
    if estimated_value < config.backtest.min_position_value:
        return _watch("目标金额低于最小持仓金额")
    if target_shares <= 0:
        return _watch("按整手数量向下取整后不足一手")
    return PositionSizingResult(
        signal="BUY",
        target_weight=target_weight,
        target_shares=target_shares,
        estimated_position_value=estimated_value,
        extra_buy_reasons=[f"研究仓位权重 {target_weight:.0%}，目标股数 {target_shares} 股"],
    )


def _target_weight(stock_score: float, config: ProjectConfig) -> float:
    sizing = config.scoring.position_sizing
    if stock_score >= sizing.strong_buy_score:
        return sizing.strong_buy_weight
    if sizing.strong_buy_score == sizing.min_buy_score:
        return sizing.base_buy_weight
    progress = (stock_score - sizing.min_buy_score) / (sizing.strong_buy_score - sizing.min_buy_score)
    progress = max(0.0, min(1.0, progress))
    return sizing.base_buy_weight + progress * (sizing.strong_buy_weight - sizing.base_buy_weight)


def _watch(reason: str) -> PositionSizingResult:
    return PositionSizingResult(
        signal="WATCH",
        target_weight=0.0,
        target_shares=0,
        estimated_position_value=0.0,
        extra_risk_reasons=[reason],
        reason_suffixes=[reason],
    )
