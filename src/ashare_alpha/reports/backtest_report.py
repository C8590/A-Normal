from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ashare_alpha.backtest import BacktestResult, SimulatedTrade
from ashare_alpha.config import ProjectConfig
from ashare_alpha.reports.models import BacktestResearchReport, BacktestSymbolSummary, REPORT_DISCLAIMER


class BacktestReportBuilder:
    def __init__(self, result: BacktestResult, config: ProjectConfig, output_dir: Path) -> None:
        self.result = result
        self.config = config
        self.output_dir = output_dir

    def build(self) -> BacktestResearchReport:
        metrics = self.result.metrics
        top_reject_reasons = self._reject_reason_counts()
        return BacktestResearchReport(
            start_date=metrics.start_date,
            end_date=metrics.end_date,
            generated_at=datetime.now(),
            output_dir=str(self.output_dir),
            initial_cash=metrics.initial_cash,
            final_equity=metrics.final_equity,
            total_return=metrics.total_return,
            annualized_return=metrics.annualized_return,
            max_drawdown=metrics.max_drawdown,
            sharpe=metrics.sharpe,
            win_rate=metrics.win_rate,
            turnover=metrics.turnover,
            trade_count=metrics.trade_count,
            filled_trade_count=metrics.filled_trade_count,
            rejected_trade_count=metrics.rejected_trade_count,
            average_holding_days=metrics.average_holding_days,
            price_source=metrics.price_source,
            execution_price_source="raw",
            valuation_price_source=metrics.price_source,
            adjusted_research_note=(
                "Adjusted valuation is for research only; execution constraints remain based on raw daily bars."
            ),
            no_trade=metrics.filled_trade_count == 0,
            no_trade_reason=self._no_trade_reason(top_reject_reasons),
            top_reject_reasons=top_reject_reasons,
            trade_summary_by_symbol=self._symbol_summary(),
            equity_curve_tail=self._equity_curve_tail(),
            initial_cash_config=self.config.backtest.initial_cash,
            max_positions=self.config.backtest.max_positions,
            max_position_weight=self.config.backtest.max_position_weight,
            rebalance_frequency=self.config.backtest.rebalance_frequency,
            execution_price=self.config.backtest.execution.execution_price,
            t_plus_one=self.config.trading_rules.t_plus_one,
            lot_size=self.config.trading_rules.lot_size,
            commission_rate=self.config.fees.commission_rate,
            min_commission=self.config.fees.min_commission,
            stamp_tax_rate_on_sell=self.config.fees.stamp_tax_rate_on_sell,
            slippage_bps=self.config.backtest.execution.slippage_bps or self.config.fees.slippage_bps,
            disclaimer=REPORT_DISCLAIMER,
        )

    def _reject_reason_counts(self) -> dict[str, int]:
        counts = Counter(trade.reject_reason or "未知拒绝原因" for trade in self.result.trades if trade.status == "REJECTED")
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def _no_trade_reason(self, top_reject_reasons: dict[str, int]) -> str | None:
        if self.result.metrics.filled_trade_count > 0:
            return None
        if self.result.metrics.trade_count == 0:
            return "样例数据和当前评分阈值下没有 BUY 信号，因此无模拟成交。"
        if top_reject_reasons:
            reason = next(iter(top_reject_reasons))
            return f"存在模拟订单但全部被拒绝，主要拒绝原因：{reason}。"
        return "回测区间内没有形成可成交的模拟订单，因此无模拟成交。"

    def _symbol_summary(self) -> list[BacktestSymbolSummary]:
        grouped: dict[str, list[SimulatedTrade]] = defaultdict(list)
        for trade in self.result.trades:
            grouped[trade.ts_code].append(trade)

        summaries = []
        for ts_code, trades in sorted(grouped.items()):
            filled = [trade for trade in trades if trade.status in {"FILLED", "PARTIAL"} and trade.filled_shares > 0]
            summaries.append(
                BacktestSymbolSummary(
                    ts_code=ts_code,
                    filled_trades=len(filled),
                    buy_count=sum(1 for trade in filled if trade.side == "BUY"),
                    sell_count=sum(1 for trade in filled if trade.side == "SELL"),
                    realized_pnl=round(sum(trade.realized_pnl or 0.0 for trade in filled), 6),
                    rejected_trades=sum(1 for trade in trades if trade.status == "REJECTED"),
                )
            )
        return summaries

    def _equity_curve_tail(self) -> list[dict]:
        tail = []
        for record in self.result.daily_equity[-5:]:
            payload = asdict(record)
            payload["trade_date"] = record.trade_date.isoformat()
            tail.append(payload)
        return tail
