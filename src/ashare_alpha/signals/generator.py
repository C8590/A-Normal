from __future__ import annotations

from collections import Counter
from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import FinancialSummary, StockMaster
from ashare_alpha.events import EventDailyRecord
from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.scoring import (
    calculate_raw_score,
    calculate_risk_penalty,
    compute_industry_strength_scores,
    compute_market_regime,
    event_component_score,
    latest_financial_by_code,
    score_fundamental_quality,
    score_trend_momentum,
    score_volatility_control,
)
from ashare_alpha.scoring.components import clamp_score
from ashare_alpha.scoring.models import ComponentScore, FundamentalScoreResult
from ashare_alpha.signals.models import SignalDailyRecord
from ashare_alpha.signals.position_sizer import BuyCandidate, PositionSizingResult, size_buy_candidates
from ashare_alpha.universe import UniverseDailyRecord


class SignalGenerator:
    def __init__(
        self,
        config: ProjectConfig,
        stock_master: list[StockMaster],
        financial_summary: list[FinancialSummary],
        universe_records: list[UniverseDailyRecord],
        factor_records: list[FactorDailyRecord],
        event_records: list[EventDailyRecord],
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self.financial_summary = financial_summary
        self.universe_by_code = {record.ts_code: record for record in universe_records}
        self.factor_by_code = {record.ts_code: record for record in factor_records}
        self.event_by_code = {record.ts_code: record for record in event_records}
        self.universe_records = universe_records
        self.factor_records = factor_records

    def generate_for_date(self, trade_date: date) -> list[SignalDailyRecord]:
        market = compute_market_regime(self.factor_records, self.universe_records)
        industry_scores = compute_industry_strength_scores(self.stock_master, self.factor_records)
        latest_financials = latest_financial_by_code(self.financial_summary, trade_date)
        drafts = [
            self._build_draft(stock, trade_date, market, industry_scores, latest_financials)
            for stock in sorted(self.stock_master, key=lambda item: item.ts_code)
        ]
        buy_candidates = [
            BuyCandidate(
                ts_code=draft["ts_code"],
                stock_score=draft["stock_score"],
                latest_close=draft["latest_close"],
            )
            for draft in sorted(
                (item for item in drafts if item["preliminary_signal"] == "BUY"),
                key=lambda item: (-item["stock_score"], item["ts_code"]),
            )
        ]
        sizing = size_buy_candidates(buy_candidates, self.config)
        return [self._finalize_record(draft, sizing.get(draft["ts_code"])) for draft in drafts]

    def _build_draft(
        self,
        stock: StockMaster,
        trade_date: date,
        market,
        industry_scores: dict[str, ComponentScore],
        latest_financials: dict[str, FinancialSummary],
    ) -> dict:
        universe = self.universe_by_code.get(stock.ts_code)
        factor = self.factor_by_code.get(stock.ts_code)
        event = self.event_by_code.get(stock.ts_code)
        fundamental = score_fundamental_quality(latest_financials.get(stock.ts_code))
        trend = score_trend_momentum(factor)
        volatility = score_volatility_control(factor)
        industry = industry_scores.get(stock.ts_code, ComponentScore(score=50.0, reasons=["行业强度缺失，使用中性分"]))
        event_component = event_component_score(event)
        liquidity_score = universe.liquidity_score if universe is not None else 0.0
        raw_score = calculate_raw_score(
            self.config,
            market.score,
            industry.score,
            trend.score,
            fundamental.score,
            liquidity_score,
            event_component.score,
            volatility.score,
        )
        penalty = calculate_risk_penalty(self.config, universe, factor, event, fundamental)
        stock_score = 0.0 if universe is not None and not universe.is_allowed else clamp_score(raw_score - penalty.risk_penalty_score)
        risk_level = penalty.risk_level
        risk_reasons = [*penalty.risk_reasons, *trend.risk_reasons, *volatility.risk_reasons, *event_component.risk_reasons]

        if event is not None and event.event_risk_score >= self.config.scoring.risk_level_thresholds.high:
            risk_level = "high"
            risk_reasons.append("公告事件风险分达到高风险阈值")

        preliminary_signal = self._preliminary_signal(universe, event, risk_level, market.regime, stock_score, risk_reasons)
        buy_reasons = self._buy_reasons(stock_score, market.reason, industry, trend, fundamental, event_component, volatility)
        return {
            "trade_date": trade_date,
            "stock": stock,
            "universe": universe,
            "factor": factor,
            "event": event,
            "market": market,
            "industry": industry,
            "trend": trend,
            "fundamental": fundamental,
            "event_component": event_component,
            "volatility": volatility,
            "liquidity_score": liquidity_score,
            "raw_score": raw_score,
            "risk_penalty_score": penalty.risk_penalty_score,
            "stock_score": stock_score,
            "risk_level": risk_level,
            "risk_reasons": _dedupe(risk_reasons),
            "buy_reasons": buy_reasons,
            "preliminary_signal": preliminary_signal,
            "latest_close": factor.latest_close if factor is not None else None,
            "ts_code": stock.ts_code,
        }

    def _preliminary_signal(
        self,
        universe: UniverseDailyRecord | None,
        event: EventDailyRecord | None,
        risk_level: str,
        market_regime: str,
        stock_score: float,
        risk_reasons: list[str],
    ) -> str:
        if universe is None:
            risk_reasons.append("缺少股票池记录")
            return "BLOCK"
        if not universe.is_allowed:
            if universe.exclude_reason_text:
                risk_reasons.append(universe.exclude_reason_text)
            return "BLOCK"
        if event is not None and event.event_block_buy:
            risk_reasons.extend(event.block_buy_reasons or ["公告事件触发禁买"])
            return "BLOCK"
        if risk_level == self.config.scoring.thresholds.block_risk_level:
            risk_reasons.append("综合风险等级为高")
            return "BLOCK"
        if market_regime == "risk":
            risk_reasons.append("市场处于风险状态，禁止新开BUY")
            return "WATCH"
        if stock_score >= self.config.scoring.thresholds.buy:
            return "BUY"
        return "WATCH"

    def _finalize_record(self, draft: dict, sizing: PositionSizingResult | None) -> SignalDailyRecord:
        signal = draft["preliminary_signal"]
        target_weight = 0.0
        target_shares = 0
        estimated_value = 0.0
        buy_reasons = list(draft["buy_reasons"])
        risk_reasons = list(draft["risk_reasons"])
        reason_suffixes: list[str] = []
        if signal == "BUY":
            if sizing is None:
                sizing = PositionSizingResult("WATCH", 0.0, 0, 0.0, reason_suffixes=["无法计算研究仓位"])
            signal = sizing.signal
            target_weight = sizing.target_weight
            target_shares = sizing.target_shares
            estimated_value = sizing.estimated_position_value
            buy_reasons.extend(sizing.extra_buy_reasons)
            risk_reasons.extend(sizing.extra_risk_reasons)
            reason_suffixes.extend(sizing.reason_suffixes)
        elif signal == "WATCH" and draft["stock_score"] < self.config.scoring.thresholds.watch:
            reason_suffixes.append("综合评分低于观察阈值")

        if signal == "BLOCK" and not risk_reasons:
            risk_reasons.append("触发风险阻断")

        return SignalDailyRecord(
            trade_date=draft["trade_date"],
            ts_code=draft["stock"].ts_code,
            symbol=draft["stock"].symbol,
            name=draft["stock"].name,
            exchange=draft["stock"].exchange,
            board=draft["stock"].board,
            industry=draft["stock"].industry,
            universe_allowed=draft["universe"].is_allowed if draft["universe"] is not None else False,
            universe_exclude_reasons=draft["universe"].exclude_reasons if draft["universe"] is not None else [],
            universe_exclude_reason_text=draft["universe"].exclude_reason_text if draft["universe"] is not None else None,
            market_regime=draft["market"].regime,
            market_regime_score=draft["market"].score,
            industry_strength_score=draft["industry"].score,
            trend_momentum_score=draft["trend"].score,
            fundamental_quality_score=draft["fundamental"].score,
            liquidity_score=draft["liquidity_score"],
            event_component_score=draft["event_component"].score,
            volatility_control_score=draft["volatility"].score,
            raw_score=draft["raw_score"],
            risk_penalty_score=draft["risk_penalty_score"],
            stock_score=draft["stock_score"],
            event_score=draft["event"].event_score if draft["event"] is not None else 0.0,
            event_risk_score=draft["event"].event_risk_score if draft["event"] is not None else 0.0,
            event_block_buy=draft["event"].event_block_buy if draft["event"] is not None else False,
            event_reason=draft["event"].event_reason if draft["event"] is not None else None,
            risk_score=draft["risk_penalty_score"],
            risk_level=draft["risk_level"],
            signal=signal,
            target_weight=target_weight,
            target_shares=target_shares,
            estimated_position_value=estimated_value,
            buy_reasons=_dedupe(buy_reasons),
            risk_reasons=_dedupe(risk_reasons),
            reason=self._reason(signal, draft, risk_reasons, buy_reasons, reason_suffixes),
        )

    def _buy_reasons(
        self,
        stock_score: float,
        market_reason: str,
        industry: ComponentScore,
        trend: ComponentScore,
        fundamental: FundamentalScoreResult,
        event_component: ComponentScore,
        volatility: ComponentScore,
    ) -> list[str]:
        reasons = [f"综合评分 {stock_score:.1f}", market_reason]
        for source in (industry, trend, fundamental, event_component, volatility):
            reasons.extend(source.reasons[:2])
        return _dedupe(reasons)

    def _reason(
        self,
        signal: str,
        draft: dict,
        risk_reasons: list[str],
        buy_reasons: list[str],
        reason_suffixes: list[str],
    ) -> str:
        prefix = f"{signal}：综合评分 {draft['stock_score']:.1f}，风险等级 {draft['risk_level']}"
        if signal == "BUY":
            return prefix + "；主要理由：" + "；".join(buy_reasons[:4])
        if signal == "BLOCK":
            return prefix + "；阻断原因：" + "；".join(_dedupe(risk_reasons)[:4])
        details = _dedupe([*reason_suffixes, *risk_reasons])
        if details:
            return prefix + "；观察原因：" + "；".join(details[:4])
        return prefix + "；未达到BUY条件，保持观察"


def summarize_signals(records: list[SignalDailyRecord]) -> dict:
    signal_counts = Counter(record.signal for record in records)
    market_regime = records[0].market_regime if records else "unknown"
    return {
        "total": len(records),
        "buy": signal_counts.get("BUY", 0),
        "watch": signal_counts.get("WATCH", 0),
        "block": signal_counts.get("BLOCK", 0),
        "high_risk": sum(1 for record in records if record.risk_level == "high"),
        "market_regime": market_regime,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result
