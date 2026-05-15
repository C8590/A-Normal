from __future__ import annotations

from ashare_alpha.events import EventDailyRecord
from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.scoring.models import ComponentScore


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def event_component_score(event: EventDailyRecord | None) -> ComponentScore:
    if event is None:
        return ComponentScore(score=50.0, reasons=["无公告事件因子，事件组件使用中性分"])
    score = clamp_score(50 + event.event_score / 2)
    reasons = [f"事件分 {event.event_score:.1f} 映射为事件组件分 {score:.1f}"]
    risk_reasons = []
    if event.event_block_buy:
        risk_reasons.append("公告事件触发禁买")
    if event.event_risk_score >= 80:
        risk_reasons.append("公告事件风险分较高")
    return ComponentScore(score=score, reasons=reasons, risk_reasons=risk_reasons)


def score_trend_momentum(factor: FactorDailyRecord | None) -> ComponentScore:
    if factor is None or not factor.is_computable:
        return ComponentScore(score=40.0, reasons=["行情因子不可计算，趋势动量保守计分"], risk_reasons=["行情因子不可计算"])

    score = 50.0
    reasons: list[str] = []
    risk_reasons: list[str] = []

    if factor.momentum_5d is not None:
        if factor.momentum_5d > 0:
            score += 10
            reasons.append("5日动量为正")
        elif factor.momentum_5d < 0:
            score -= 5
            risk_reasons.append("5日动量为负")
    if factor.momentum_20d is not None:
        if factor.momentum_20d > 0:
            score += 15
            reasons.append("20日动量为正")
        elif factor.momentum_20d < 0:
            score -= 10
            risk_reasons.append("20日动量为负")
    if factor.momentum_60d is not None:
        if factor.momentum_60d > 0:
            score += 15
            reasons.append("60日动量为正")
        elif factor.momentum_60d < 0:
            score -= 10
            risk_reasons.append("60日动量为负")
    if factor.close_above_ma20 is True:
        score += 10
        reasons.append("收盘价站上20日均线")
    elif factor.close_above_ma20 is False:
        score -= 5
        risk_reasons.append("收盘价低于20日均线")
    if factor.close_above_ma60 is True:
        score += 10
        reasons.append("收盘价站上60日均线")
    elif factor.close_above_ma60 is False:
        score -= 5
        risk_reasons.append("收盘价低于60日均线")

    return ComponentScore(score=clamp_score(score), reasons=reasons, risk_reasons=risk_reasons)


def score_volatility_control(factor: FactorDailyRecord | None) -> ComponentScore:
    if factor is None or not factor.is_computable:
        return ComponentScore(score=50.0, reasons=["行情因子不可计算，波动控制使用中性偏保守分"], risk_reasons=["行情因子不可计算"])

    score = 70.0
    reasons: list[str] = []
    risk_reasons: list[str] = []

    if factor.volatility_20d is not None:
        if factor.volatility_20d <= 0.01:
            score += 15
            reasons.append("20日波动率较低")
        elif factor.volatility_20d <= 0.02:
            score += 5
            reasons.append("20日波动率温和")
        elif factor.volatility_20d > 0.05:
            score -= 25
            risk_reasons.append("20日波动率较高")
    if factor.max_drawdown_20d is not None:
        if factor.max_drawdown_20d <= -0.15:
            score -= 25
            risk_reasons.append("20日最大回撤较大")
        elif factor.max_drawdown_20d <= -0.08:
            score -= 10
            risk_reasons.append("20日最大回撤偏大")
    if factor.limit_down_recent_count > 0:
        penalty = 10 * factor.limit_down_recent_count
        score -= penalty
        risk_reasons.append(f"近窗口出现跌停 {factor.limit_down_recent_count} 次")

    return ComponentScore(score=clamp_score(score), reasons=reasons, risk_reasons=risk_reasons)
