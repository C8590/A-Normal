from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.config import DEFAULT_CONFIG_DIR, _read_yaml
from a_normal.data.models import _validate_date_format
from a_normal.factors import EventScoreResult, FactorDaily
from a_normal.universe import UniverseDaily


Signal = Literal["BUY", "WATCH", "HOLD", "SELL", "BLOCK"]
RiskLevel = Literal["low", "medium", "high"]
MarketRegime = Literal["normal", "risk"]


class ScoringThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    buy_score: float = 70
    watch_score: float = 55
    sell_score: float = 40
    high_risk_score: float = Field(default=0.7, ge=0, le=1)
    medium_risk_score: float = Field(default=0.4, ge=0, le=1)
    universe_high_risk_below: float = Field(default=0.3, ge=0, le=1)


class ScoringNormalization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    momentum_abs_cap: float = Field(default=0.2, gt=0)
    volatility_cap: float = Field(default=0.08, gt=0)
    drawdown_cap: float = Field(default=0.2, gt=0)
    amount_mean_cap: float = Field(default=100_000_000.0, gt=0)
    turnover_mean_cap: float = Field(default=0.08, gt=0)
    limit_count_cap: int = Field(default=3, gt=0)


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capital: float = Field(default=10_000, gt=0)
    lot_size: int = Field(default=100, gt=0)
    max_single_position_pct: float = Field(default=0.2, gt=0, le=1)
    thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)
    weights: dict[str, float] = Field(default_factory=dict)
    normalization: ScoringNormalization = Field(default_factory=ScoringNormalization)


class SignalDaily(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str
    trade_date: date
    stock_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    signal: Signal
    target_weight: float = Field(ge=0, le=1)
    reason: str

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value):
        return _validate_date_format(value)


def load_scoring_config(config_dir: str | Path | None = None) -> ScoringConfig:
    base_dir = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    return ScoringConfig.model_validate(_read_yaml(base_dir / "scoring.yaml"))


def build_signals(
    universe_daily: list[UniverseDaily],
    factor_daily: list[FactorDaily],
    event_scores: list[EventScoreResult],
    market_regime: MarketRegime | str,
    as_of_date: str | date,
    config: ScoringConfig | None = None,
) -> list[SignalDaily]:
    scoring_config = config or load_scoring_config()
    target_date = _parse_date(as_of_date)
    factor_by_code = {item.ts_code: item for item in factor_daily if item.trade_date == target_date}
    latest_event_by_code = _latest_event_scores(event_scores)

    rows = []
    for universe in sorted(universe_daily, key=lambda item: item.ts_code):
        factor = factor_by_code.get(universe.ts_code)
        event = latest_event_by_code.get(universe.ts_code)
        stock_score = _stock_score(universe, factor, event, scoring_config)
        risk_level = _risk_level(universe, factor, event, scoring_config)
        signal = _signal(universe, stock_score, risk_level, event, str(market_regime), scoring_config)
        target_weight = _target_weight(signal, stock_score, factor, scoring_config)
        reason = _reason(universe, factor, event, stock_score, risk_level, signal, target_weight, str(market_regime))
        rows.append(
            SignalDaily(
                ts_code=universe.ts_code,
                trade_date=target_date,
                stock_score=stock_score,
                risk_level=risk_level,
                signal=signal,
                target_weight=target_weight,
                reason=reason,
            )
        )
    return rows


def save_signals_csv(signals: list[SignalDaily], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ts_code", "trade_date", "stock_score", "risk_level", "signal", "target_weight", "reason"]
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for signal in signals:
            writer.writerow(signal.model_dump(mode="json"))


def save_signals_markdown(signals: list[SignalDaily], path: str | Path, title: str | None = None) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title or 'A股信号报告'}", "", "| 代码 | 信号 | 分数 | 风险 | 目标权重 | 原因 |", "| --- | --- | ---: | --- | ---: | --- |"]
    for item in signals:
        lines.append(
            f"| {item.ts_code} | {item.signal} | {item.stock_score:.2f} | {item.risk_level} | "
            f"{item.target_weight:.4f} | {item.reason} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    _validate_date_format(value)
    return date.fromisoformat(value)


def _latest_event_scores(event_scores: list[EventScoreResult]) -> dict[str, EventScoreResult]:
    by_code: dict[str, EventScoreResult] = {}
    for event in event_scores:
        current = by_code.get(event.stock_code)
        if current is None or event.event_date > current.event_date:
            by_code[event.stock_code] = event
    return by_code


def _stock_score(
    universe: UniverseDaily,
    factor: FactorDaily | None,
    event: EventScoreResult | None,
    config: ScoringConfig,
) -> float:
    components = _components(universe, factor, event, config)
    weighted_sum = 0.0
    total_weight = 0.0
    for name, value in components.items():
        weight = config.weights.get(name, 0.0)
        if weight == 0:
            continue
        weighted_sum += weight * value
        total_weight += abs(weight)
    if total_weight == 0:
        return 50.0
    return round(_clamp((weighted_sum / total_weight + 1.0) * 50.0, 0.0, 100.0), 4)


def _components(
    universe: UniverseDaily,
    factor: FactorDaily | None,
    event: EventScoreResult | None,
    config: ScoringConfig,
) -> dict[str, float]:
    n = config.normalization
    return {
        "momentum_5d": _signed(getattr(factor, "momentum_5d", None), n.momentum_abs_cap),
        "momentum_20d": _signed(getattr(factor, "momentum_20d", None), n.momentum_abs_cap),
        "momentum_60d": _signed(getattr(factor, "momentum_60d", None), n.momentum_abs_cap),
        "volatility_20d": _positive(getattr(factor, "volatility_20d", None), n.volatility_cap),
        "max_drawdown_20d": _signed(getattr(factor, "max_drawdown_20d", None), n.drawdown_cap),
        "amount_mean_20d": _positive(getattr(factor, "amount_mean_20d", None), n.amount_mean_cap),
        "turnover_mean_20d": _positive(getattr(factor, "turnover_mean_20d", None), n.turnover_mean_cap),
        "close_above_ma20": _bool_score(getattr(factor, "close_above_ma20", None)),
        "close_above_ma60": _bool_score(getattr(factor, "close_above_ma60", None)),
        "limit_up_recent_count": _positive(getattr(factor, "limit_up_recent_count", 0), n.limit_count_cap),
        "limit_down_recent_count": _positive(getattr(factor, "limit_down_recent_count", 0), n.limit_count_cap),
        "universe_liquidity_score": _clamp(universe.liquidity_score, 0, 1),
        "universe_risk_score": _clamp(universe.risk_score, 0, 1),
        "event_score": _signed(getattr(event, "event_score", None), 1.0),
        "event_risk_score": _positive(getattr(event, "event_risk_score", None), 1.0),
    }


def _risk_level(
    universe: UniverseDaily,
    factor: FactorDaily | None,
    event: EventScoreResult | None,
    config: ScoringConfig,
) -> RiskLevel:
    event_risk = event.event_risk_score if event is not None else 0.0
    volatility = factor.volatility_20d if factor is not None and factor.volatility_20d is not None else 0.0
    if (
        universe.risk_score <= config.thresholds.universe_high_risk_below
        or event_risk >= config.thresholds.high_risk_score
        or (event is not None and event.event_block_buy)
    ):
        return "high"
    if event_risk >= config.thresholds.medium_risk_score or volatility >= config.normalization.volatility_cap:
        return "medium"
    return "low"


def _signal(
    universe: UniverseDaily,
    stock_score: float,
    risk_level: RiskLevel,
    event: EventScoreResult | None,
    market_regime: str,
    config: ScoringConfig,
) -> Signal:
    if not universe.is_allowed:
        return "BLOCK"
    if risk_level == "high" or (event is not None and event.event_block_buy):
        return "BLOCK"
    if stock_score >= config.thresholds.buy_score:
        return "WATCH" if market_regime == "risk" else "BUY"
    if stock_score >= config.thresholds.watch_score:
        return "WATCH"
    if stock_score < config.thresholds.sell_score:
        return "SELL"
    return "HOLD"


def _target_weight(signal: Signal, stock_score: float, factor: FactorDaily | None, config: ScoringConfig) -> float:
    if signal not in {"BUY", "HOLD"} or factor is None or factor.close is None or factor.close <= 0:
        return 0.0
    raw_weight = config.max_single_position_pct * _clamp(stock_score / 100.0, 0.0, 1.0)
    max_budget = config.capital * min(raw_weight, config.max_single_position_pct)
    lot_value = factor.close * config.lot_size
    lots = int(max_budget // lot_value)
    if lots <= 0:
        return 0.0
    return round((lots * lot_value) / config.capital, 6)


def _reason(
    universe: UniverseDaily,
    factor: FactorDaily | None,
    event: EventScoreResult | None,
    stock_score: float,
    risk_level: RiskLevel,
    signal: Signal,
    target_weight: float,
    market_regime: str,
) -> str:
    parts = [f"综合评分{stock_score:.1f}，风险等级{risk_level}，信号为{signal}。"]
    if not universe.is_allowed:
        parts.append(f"股票池未通过，原因：{','.join(universe.exclude_reasons)}。")
    if market_regime == "risk":
        parts.append("市场处于风险状态，禁止买入。")
    if event is not None:
        parts.append(f"公告影响：{event.event_type}，事件分{event.event_score:.2f}，风险分{event.event_risk_score:.2f}。")
        if event.event_block_buy:
            parts.append("高风险公告触发禁买。")
    if factor is None:
        parts.append("缺少因子数据。")
    elif factor.close is None:
        parts.append("缺少收盘价，目标权重设为0。")
    elif target_weight == 0 and signal in {"BUY", "HOLD"}:
        parts.append("本金不足以按100股整数倍合理建仓。")
    elif target_weight > 0:
        parts.append(f"按本金和100股整数倍约束，目标权重{target_weight:.2%}。")
    return "".join(parts)


def _signed(value: float | int | None, cap: float) -> float:
    if value is None:
        return 0.0
    return _clamp(float(value) / cap, -1.0, 1.0)


def _positive(value: float | int | None, cap: float) -> float:
    if value is None:
        return 0.0
    return _clamp(float(value) / cap, 0.0, 1.0)


def _bool_score(value: bool | None) -> float:
    if value is None:
        return 0.0
    return 1.0 if value else -1.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
