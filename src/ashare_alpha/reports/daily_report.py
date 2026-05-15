from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import StockMaster
from ashare_alpha.events import EventDailyRecord
from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.reports.models import DailyResearchReport, REPORT_DISCLAIMER, ReportStockItem
from ashare_alpha.signals import SignalDailyRecord
from ashare_alpha.universe import UniverseDailyRecord


class DailyReportBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        stock_master: list[StockMaster],
        universe_records: list[UniverseDailyRecord],
        factor_records: list[FactorDailyRecord],
        event_records: list[EventDailyRecord],
        signal_records: list[SignalDailyRecord],
        data_dir: Path,
        config_dir: Path,
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self.universe_records = universe_records
        self.factor_records = factor_records
        self.event_records = event_records
        self.signal_records = signal_records
        self.data_dir = data_dir
        self.config_dir = config_dir
        self._stock_by_code = {stock.ts_code: stock for stock in stock_master}
        self._universe_by_code = {record.ts_code: record for record in universe_records}
        self._factor_by_code = {record.ts_code: record for record in factor_records}
        self._event_by_code = {record.ts_code: record for record in event_records}

    def build(self, report_date: date) -> DailyResearchReport:
        items = [self._item_from_signal(signal) for signal in self.signal_records if signal.trade_date == report_date]
        buy_candidates = sorted(
            (item for item in items if item.signal == "BUY"),
            key=lambda item: (-item.stock_score, item.ts_code),
        )
        watch_candidates = sorted(
            (item for item in items if item.signal == "WATCH"),
            key=lambda item: (-item.stock_score, item.ts_code),
        )[:20]
        blocked_stocks = sorted(
            (item for item in items if item.signal == "BLOCK" or item.universe_exclude_reason_text),
            key=lambda item: (-self._risk_score(item.ts_code), -item.stock_score, item.ts_code),
        )[:50]
        high_risk_stocks = sorted(
            (item for item in items if item.risk_level == "high" or (item.event_risk_score or 0) >= 60),
            key=lambda item: (-(item.event_risk_score or self._risk_score(item.ts_code)), -item.stock_score, item.ts_code),
        )
        recent_event_risk_stocks = sorted(
            (item for item in items if (item.event_risk_score or 0) > 0 or self._event_block_buy(item.ts_code)),
            key=lambda item: (-(item.event_risk_score or 0), item.ts_code),
        )
        signal_counts = Counter(item.signal for item in items)
        universe_reason_counts: Counter[str] = Counter()
        for record in self.universe_records:
            if record.trade_date == report_date:
                universe_reason_counts.update(record.exclude_reasons)

        return DailyResearchReport(
            report_date=report_date,
            generated_at=datetime.now(),
            data_dir=str(self.data_dir),
            config_dir=str(self.config_dir),
            total_stocks=len(self.stock_master),
            allowed_universe_count=sum(1 for record in self.universe_records if record.trade_date == report_date and record.is_allowed),
            blocked_universe_count=sum(
                1 for record in self.universe_records if record.trade_date == report_date and not record.is_allowed
            ),
            buy_count=signal_counts.get("BUY", 0),
            watch_count=signal_counts.get("WATCH", 0),
            block_count=signal_counts.get("BLOCK", 0),
            high_risk_count=sum(1 for item in items if item.risk_level == "high"),
            market_regime=self._market_regime(),
            market_regime_score=self._market_regime_score(),
            buy_candidates=buy_candidates,
            watch_candidates=watch_candidates,
            blocked_stocks=blocked_stocks,
            high_risk_stocks=high_risk_stocks,
            recent_event_risk_stocks=recent_event_risk_stocks,
            universe_exclude_reason_counts=dict(sorted(universe_reason_counts.items())),
            signal_reason_counts=self._signal_reason_counts(items),
            event_block_buy_count=sum(
                1 for record in self.event_records if record.trade_date == report_date and record.event_block_buy
            ),
            event_high_risk_count=sum(
                1 for record in self.event_records if record.trade_date == report_date and record.event_risk_score >= 60
            ),
            average_stock_score=_average([item.stock_score for item in items]),
            average_risk_score=_average([self._risk_score(item.ts_code) for item in items]),
            initial_cash=self.config.backtest.initial_cash,
            max_positions=self.config.backtest.max_positions,
            max_position_weight=self.config.backtest.max_position_weight,
            lot_size=self.config.trading_rules.lot_size,
            commission_rate=self.config.fees.commission_rate,
            min_commission=self.config.fees.min_commission,
            stamp_tax_rate_on_sell=self.config.fees.stamp_tax_rate_on_sell,
            slippage_bps=self._slippage_bps(),
            disclaimer=REPORT_DISCLAIMER,
        )

    def _item_from_signal(self, signal: SignalDailyRecord) -> ReportStockItem:
        factor = self._factor_by_code.get(signal.ts_code)
        event = self._event_by_code.get(signal.ts_code)
        stock = self._stock_by_code.get(signal.ts_code)
        reason = self._clean_reason(signal)
        return ReportStockItem(
            ts_code=signal.ts_code,
            name=signal.name or (stock.name if stock is not None else signal.ts_code),
            industry=signal.industry,
            signal=signal.signal,
            stock_score=signal.stock_score,
            risk_level=signal.risk_level,
            target_weight=signal.target_weight,
            target_shares=signal.target_shares,
            estimated_position_value=signal.estimated_position_value,
            latest_close=factor.latest_close if factor is not None else None,
            liquidity_score=signal.liquidity_score,
            event_score=signal.event_score,
            event_risk_score=signal.event_risk_score,
            reason=reason,
            buy_reasons=signal.buy_reasons,
            risk_reasons=signal.risk_reasons,
            universe_exclude_reason_text=signal.universe_exclude_reason_text if not signal.universe_allowed else None,
            event_reason=event.event_reason if event is not None and event.event_count > 0 else signal.event_reason,
        )

    def _clean_reason(self, signal: SignalDailyRecord) -> str:
        if not signal.universe_allowed and signal.universe_exclude_reason_text:
            return f"禁买：股票池过滤未通过，剔除原因：{signal.universe_exclude_reason_text}。"
        if signal.event_block_buy and signal.event_reason:
            return f"禁买：公告事件触发禁买规则，事件说明：{signal.event_reason}。"
        if signal.signal == "BUY":
            return f"BUY：综合评分 {signal.stock_score:.1f}，风险等级 {signal.risk_level}，建议按配置控制仓位。"
        if self._looks_max_position_downgrade(signal):
            return (
                f"WATCH：综合评分 {signal.stock_score:.1f} 已达到 BUY 阈值，"
                "但受最大持仓数量、最小成交金额或仓位约束影响，当前降级为观察。"
            )
        if signal.signal == "WATCH":
            return f"WATCH：综合评分 {signal.stock_score:.1f}，暂未满足 BUY 执行条件，保持观察。"
        if signal.risk_reasons:
            return f"禁买：风险等级 {signal.risk_level}，主要原因：{'；'.join(signal.risk_reasons[:3])}。"
        return f"{signal.signal}：综合评分 {signal.stock_score:.1f}，风险等级 {signal.risk_level}。"

    def _looks_max_position_downgrade(self, signal: SignalDailyRecord) -> bool:
        return (
            signal.signal == "WATCH"
            and signal.universe_allowed
            and not signal.event_block_buy
            and signal.stock_score >= self.config.scoring.thresholds.buy
        )

    def _market_regime(self) -> str:
        if self.signal_records:
            return self.signal_records[0].market_regime
        return "unknown"

    def _market_regime_score(self) -> float:
        if self.signal_records:
            return self.signal_records[0].market_regime_score
        return 0.0

    def _event_block_buy(self, ts_code: str) -> bool:
        event = self._event_by_code.get(ts_code)
        return bool(event and event.event_block_buy)

    def _risk_score(self, ts_code: str) -> float:
        universe = self._universe_by_code.get(ts_code)
        if universe is not None:
            return universe.risk_score
        signal = next((record for record in self.signal_records if record.ts_code == ts_code), None)
        return signal.risk_score if signal is not None else 0.0

    def _slippage_bps(self) -> float:
        return self.config.backtest.execution.slippage_bps or self.config.fees.slippage_bps

    @staticmethod
    def _signal_reason_counts(items: list[ReportStockItem]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for item in items:
            if item.universe_exclude_reason_text:
                counts["股票池过滤"] += 1
            elif item.event_reason and item.signal == "BLOCK":
                counts["公告事件禁买"] += 1
            else:
                counts[item.signal] += 1
        return dict(sorted(counts.items()))


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)
