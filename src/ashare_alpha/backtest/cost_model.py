from __future__ import annotations

import math

from ashare_alpha.config import ProjectConfig
from ashare_alpha.backtest.models import TradeCost


class CostModel:
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.slippage_bps = (
            config.backtest.execution.slippage_bps
            if config.backtest.execution.slippage_bps is not None
            else config.fees.slippage_bps
        )

    def apply_slippage(self, price: float, side: str) -> float:
        tick = self.config.trading_rules.price_tick
        if side == "BUY":
            adjusted = price * (1 + self.slippage_bps / 10000)
            return math.ceil((adjusted - 1e-12) / tick) * tick
        if side == "SELL":
            adjusted = price * (1 - self.slippage_bps / 10000)
            return math.floor((adjusted + 1e-12) / tick) * tick
        raise ValueError("side must be BUY or SELL")

    def calculate_trade_cost(self, side: str, price: float, shares: int) -> TradeCost:
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if shares < 0:
            raise ValueError("shares must be non-negative")
        gross_value = price * shares
        if shares == 0:
            commission = 0.0
        else:
            commission = max(gross_value * self.config.fees.commission_rate, self.config.fees.min_commission)
        stamp_tax = gross_value * self.config.fees.stamp_tax_rate_on_sell if side == "SELL" else 0.0
        transfer_fee = gross_value * self.config.fees.transfer_fee_rate
        total_fee = commission + stamp_tax + transfer_fee
        net_cash_change = -(gross_value + total_fee) if side == "BUY" else gross_value - total_fee
        return TradeCost(
            gross_value=gross_value,
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            net_cash_change=net_cash_change,
        )
