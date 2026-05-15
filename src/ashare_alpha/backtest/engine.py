from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from ashare_alpha.backtest.broker_simulator import BrokerSimulator
from ashare_alpha.backtest.cost_model import CostModel
from ashare_alpha.backtest.metrics import calculate_metrics
from ashare_alpha.backtest.models import BacktestResult, DailyEquityRecord, SimulatedOrder, SimulatedTrade
from ashare_alpha.backtest.portfolio import Portfolio
from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.signals import SignalDailyRecord, SignalGenerator
from ashare_alpha.universe import UniverseBuilder


def get_trading_dates(daily_bars: list[DailyBar], start_date: date, end_date: date) -> list[date]:
    dates = {
        bar.trade_date
        for bar in daily_bars
        if start_date <= bar.trade_date <= end_date and bar.is_trading
    }
    return sorted(dates)


def select_rebalance_dates(trading_dates: list[date], frequency: str) -> list[date]:
    if frequency == "daily":
        return list(trading_dates)
    if frequency not in {"weekly", "monthly"}:
        raise ValueError("rebalance frequency must be daily, weekly, or monthly")
    grouped: dict[tuple[int, int] | tuple[int, int, int], list[date]] = defaultdict(list)
    for trade_date in trading_dates:
        if frequency == "weekly":
            iso_year, iso_week, _ = trade_date.isocalendar()
            grouped[(iso_year, iso_week)].append(trade_date)
        else:
            grouped[(trade_date.year, trade_date.month)].append(trade_date)
    return [max(group) for group in grouped.values()]


class BacktestEngine:
    def __init__(
        self,
        config: ProjectConfig,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self.daily_bars = daily_bars
        self.financial_summary = financial_summary
        self.announcement_events = announcement_events
        self._bars_by_date_code = {(bar.trade_date, bar.ts_code): bar for bar in daily_bars}

    def run(self, start_date: date, end_date: date) -> BacktestResult:
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        trading_dates = get_trading_dates(self.daily_bars, start_date, end_date)
        if not trading_dates:
            raise ValueError("No trading dates available in the requested range")

        rebalance_dates = set(select_rebalance_dates(trading_dates, self.config.backtest.rebalance_frequency))
        portfolio = Portfolio(self.config.backtest.initial_cash, self.config.trading_rules)
        cost_model = CostModel(self.config)
        broker = BrokerSimulator(self.config, cost_model, portfolio)
        trades: list[SimulatedTrade] = []
        daily_equity: list[DailyEquityRecord] = []
        pending_orders: list[SimulatedOrder] = []
        last_price_map: dict[str, float] = {}
        running_max = self.config.backtest.initial_cash
        previous_equity = self.config.backtest.initial_cash

        for index, trade_date in enumerate(trading_dates):
            todays_orders = [order for order in pending_orders if order.execution_date == trade_date]
            pending_orders = [order for order in pending_orders if order.execution_date != trade_date]
            for order in sorted(todays_orders, key=lambda item: 0 if item.side == "SELL" else 1):
                trades.append(broker.execute_order(order, self._bars_by_date_code.get((trade_date, order.ts_code))))

            self._update_last_prices(trade_date, last_price_map)
            snapshots = portfolio.mark_to_market(trade_date, last_price_map)
            market_value = sum(snapshot.market_value for snapshot in snapshots)
            total_equity = portfolio.cash + market_value
            daily_return = total_equity / previous_equity - 1 if previous_equity > 0 else 0.0
            running_max = max(running_max, total_equity)
            drawdown = total_equity / running_max - 1 if running_max > 0 else 0.0
            daily_equity.append(
                DailyEquityRecord(
                    trade_date=trade_date,
                    cash=portfolio.cash,
                    market_value=market_value,
                    total_equity=total_equity,
                    positions_count=sum(1 for snapshot in snapshots if snapshot.shares > 0),
                    gross_exposure=market_value / total_equity if total_equity > 0 else 0.0,
                    daily_return=daily_return,
                    drawdown=drawdown,
                )
            )
            previous_equity = total_equity

            if trade_date in rebalance_dates and index + 1 < len(trading_dates):
                execution_date = trading_dates[index + 1]
                signals = self._generate_signals(trade_date)
                pending_orders = self._build_orders(signals, trade_date, execution_date, total_equity, portfolio)

        metrics = calculate_metrics(
            daily_equity=daily_equity,
            trades=trades,
            initial_cash=self.config.backtest.initial_cash,
            annualization_days=self.config.backtest.metrics.annualization_days,
        )
        return BacktestResult(metrics=metrics, trades=trades, daily_equity=daily_equity)

    def _generate_signals(self, decision_date: date) -> list[SignalDailyRecord]:
        universe_records = UniverseBuilder(
            config=self.config,
            stock_master=self.stock_master,
            daily_bars=self.daily_bars,
            financial_summary=self.financial_summary,
            announcement_events=self.announcement_events,
        ).build_for_date(decision_date)
        factor_records = FactorBuilder(
            config=self.config,
            daily_bars=self.daily_bars,
            stock_master=self.stock_master,
        ).build_for_date(decision_date)
        event_records = EventFeatureBuilder(
            config=self.config,
            announcement_events=self.announcement_events,
            stock_master=self.stock_master,
        ).build_for_date(decision_date)
        return SignalGenerator(
            config=self.config,
            stock_master=self.stock_master,
            financial_summary=self.financial_summary,
            universe_records=universe_records,
            factor_records=factor_records,
            event_records=event_records,
        ).generate_for_date(decision_date)

    def _build_orders(
        self,
        signals: list[SignalDailyRecord],
        decision_date: date,
        execution_date: date,
        current_equity: float,
        portfolio: Portfolio,
    ) -> list[SimulatedOrder]:
        signal_by_code = {signal.ts_code: signal for signal in signals}
        orders: list[SimulatedOrder] = []
        buy_orders: list[SimulatedOrder] = []
        for signal in signals:
            current_shares = portfolio.get_total_shares(signal.ts_code)
            target_weight = self._target_weight(signal, current_shares)
            bar = self._bars_by_date_code.get((execution_date, signal.ts_code))
            execution_price = bar.open if bar is not None else None
            target_shares = self._target_shares(current_equity, target_weight, execution_price)
            if target_weight > 0 and execution_price is not None and target_shares * execution_price < self.config.backtest.min_position_value:
                target_shares = 0
            if target_shares < current_shares:
                orders.append(
                    SimulatedOrder(
                        decision_date=decision_date,
                        execution_date=execution_date,
                        ts_code=signal.ts_code,
                        side="SELL",
                        requested_shares=current_shares - target_shares,
                        target_weight=target_weight,
                        reason=f"模拟调仓卖出：{signal.reason}",
                    )
                )
            elif target_shares > current_shares:
                buy_orders.append(
                    SimulatedOrder(
                        decision_date=decision_date,
                        execution_date=execution_date,
                        ts_code=signal.ts_code,
                        side="BUY",
                        requested_shares=target_shares - current_shares,
                        target_weight=target_weight,
                        reason=f"模拟调仓买入：{signal.reason}",
                    )
                )

        held_codes = set(portfolio.lots_by_symbol) - set(signal_by_code)
        for ts_code in sorted(held_codes):
            current_shares = portfolio.get_total_shares(ts_code)
            if current_shares > 0:
                orders.append(
                    SimulatedOrder(
                        decision_date=decision_date,
                        execution_date=execution_date,
                        ts_code=ts_code,
                        side="SELL",
                        requested_shares=current_shares,
                        target_weight=0,
                        reason="模拟调仓卖出：持仓股票缺少当日信号",
                    )
                )

        buy_orders.sort(key=lambda order: (-signal_by_code[order.ts_code].stock_score, order.ts_code))
        active_buys = [order for order in buy_orders if order.requested_shares > 0][: self.config.backtest.max_positions]
        return [*orders, *active_buys]

    def _target_weight(self, signal: SignalDailyRecord, current_shares: int) -> float:
        if signal.signal == "BUY":
            return signal.target_weight
        if signal.signal == "BLOCK" and current_shares > 0 and self.config.backtest.execution.exit_on_block:
            return 0.0
        if signal.signal != "BUY" and current_shares > 0 and self.config.backtest.execution.sell_when_signal_not_buy:
            return 0.0
        return 0.0

    def _target_shares(self, equity: float, target_weight: float, execution_price: float | None) -> int:
        if target_weight <= 0 or execution_price is None or execution_price <= 0:
            return 0
        lot_size = self.config.trading_rules.lot_size
        raw_shares = equity * min(target_weight, self.config.backtest.max_position_weight) / execution_price
        return math.floor(raw_shares / lot_size) * lot_size

    def _update_last_prices(self, trade_date: date, last_price_map: dict[str, float]) -> None:
        for bar in self.daily_bars:
            if bar.trade_date == trade_date and bar.is_trading:
                last_price_map[bar.ts_code] = bar.close
