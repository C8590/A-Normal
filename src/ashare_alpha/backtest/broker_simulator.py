from __future__ import annotations

from ashare_alpha.backtest.cost_model import CostModel
from ashare_alpha.backtest.models import SimulatedOrder, SimulatedTrade
from ashare_alpha.backtest.portfolio import Portfolio
from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import DailyBar


class BrokerSimulator:
    def __init__(
        self,
        config: ProjectConfig,
        cost_model: CostModel,
        portfolio: Portfolio,
        price_source: str = "raw",
    ) -> None:
        self.config = config
        self.cost_model = cost_model
        self.portfolio = portfolio
        self.price_source = price_source

    def execute_order(self, order: SimulatedOrder, execution_bar: DailyBar | None) -> SimulatedTrade:
        if execution_bar is None:
            return self._rejected(order, "执行日无行情数据")
        if not execution_bar.is_trading:
            return self._rejected(order, "执行日停牌或未交易")
        raw_price = self._execution_price(execution_bar)
        if order.side == "BUY" and self._is_limit_up_buy(raw_price, execution_bar):
            return self._rejected(order, "涨停价附近，模拟买入失败")
        if order.side == "SELL" and self._is_limit_down_sell(raw_price, execution_bar):
            return self._rejected(order, "跌停价附近，模拟卖出失败")

        price = self.cost_model.apply_slippage(raw_price, order.side)
        cost = self.cost_model.calculate_trade_cost(order.side, price, order.requested_shares)
        if order.side == "BUY":
            if self.portfolio.cash + cost.net_cash_change < -1e-9:
                return self._rejected(order, "现金不足")
            cost_per_share = (cost.gross_value + cost.total_fee) / order.requested_shares
            self.portfolio.buy(order.ts_code, order.requested_shares, cost_per_share, order.execution_date, cost.net_cash_change)
            realized_pnl = None
            holding_days = None
        else:
            if order.requested_shares > self.portfolio.get_available_shares(order.ts_code, order.execution_date):
                return self._rejected(order, "T+1 或可用股份不足")
            realized_pnl, holding_days = self.portfolio.sell(
                order.ts_code,
                order.requested_shares,
                order.execution_date,
                cost.net_cash_change,
            )

        return SimulatedTrade(
            decision_date=order.decision_date,
            execution_date=order.execution_date,
            ts_code=order.ts_code,
            side=order.side,
            requested_shares=order.requested_shares,
            filled_shares=order.requested_shares,
            price=price,
            gross_value=cost.gross_value,
            commission=cost.commission,
            stamp_tax=cost.stamp_tax,
            transfer_fee=cost.transfer_fee,
            total_fee=cost.total_fee,
            net_cash_change=cost.net_cash_change,
            status="FILLED",
            reject_reason=None,
            realized_pnl=realized_pnl,
            holding_days=holding_days,
            reason=order.reason,
            price_source=self.price_source,
            execution_price_source="raw",
            valuation_price_source=self.price_source,
        )

    def _execution_price(self, bar: DailyBar) -> float:
        if self.config.backtest.execution.execution_price == "next_open":
            return bar.open
        raise ValueError("unsupported execution_price")

    def _is_limit_up_buy(self, price: float, bar: DailyBar) -> bool:
        return (
            self.config.trading_rules.block_buy_at_limit_up
            and bar.limit_up is not None
            and price >= bar.limit_up - self.config.trading_rules.price_tick / 2
        )

    def _is_limit_down_sell(self, price: float, bar: DailyBar) -> bool:
        return (
            self.config.trading_rules.block_sell_at_limit_down
            and bar.limit_down is not None
            and price <= bar.limit_down + self.config.trading_rules.price_tick / 2
        )

    def _rejected(self, order: SimulatedOrder, reason: str) -> SimulatedTrade:
        return SimulatedTrade(
            decision_date=order.decision_date,
            execution_date=order.execution_date,
            ts_code=order.ts_code,
            side=order.side,
            requested_shares=order.requested_shares,
            filled_shares=0,
            price=None,
            gross_value=0.0,
            commission=0.0,
            stamp_tax=0.0,
            transfer_fee=0.0,
            total_fee=0.0,
            net_cash_change=0.0,
            status="REJECTED",
            reject_reason=reason,
            realized_pnl=None,
            holding_days=None,
            reason=order.reason,
            price_source=self.price_source,
            execution_price_source="raw",
            valuation_price_source=self.price_source,
        )
