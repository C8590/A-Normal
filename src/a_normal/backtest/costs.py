from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from a_normal.config import FeesConfig, TradingRulesConfig, load_config


Side = Literal["BUY", "SELL"]


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_price: float = Field(ge=0)
    gross_amount: float = Field(ge=0)
    commission: float = Field(ge=0)
    stamp_tax: float = Field(ge=0)
    total_cost: float = Field(ge=0)


class CostModel:
    def __init__(
        self,
        fees: FeesConfig | None = None,
        trading_rules: TradingRulesConfig | None = None,
    ) -> None:
        config = load_config()
        self.fees = fees or config.fees
        self.trading_rules = trading_rules or config.trading_rules

    def round_price(self, price: float) -> float:
        tick = Decimal(str(self.trading_rules.price_tick))
        return float(Decimal(str(price)).quantize(tick, rounding=ROUND_HALF_UP))

    def execution_price(self, price: float, side: Side) -> float:
        multiplier = 1 + self.fees.slippage_bps / 10000 if side == "BUY" else 1 - self.fees.slippage_bps / 10000
        return self.round_price(max(0.0, price * multiplier))

    def calculate(self, price: float, shares: int, side: Side) -> CostBreakdown:
        if shares <= 0 or price <= 0:
            return CostBreakdown(execution_price=0, gross_amount=0, commission=0, stamp_tax=0, total_cost=0)

        execution_price = self.execution_price(price, side)
        gross_amount = round(execution_price * shares, 6)
        commission = round(max(gross_amount * self.fees.commission_rate, self.fees.min_commission), 6)
        stamp_tax = round(gross_amount * self.fees.stamp_tax_rate_on_sell, 6) if side == "SELL" else 0.0
        return CostBreakdown(
            execution_price=execution_price,
            gross_amount=gross_amount,
            commission=commission,
            stamp_tax=stamp_tax,
            total_cost=round(commission + stamp_tax, 6),
        )

    def cash_delta(self, price: float, shares: int, side: Side) -> float:
        cost = self.calculate(price, shares, side)
        if side == "BUY":
            return -round(cost.gross_amount + cost.total_cost, 6)
        return round(cost.gross_amount - cost.total_cost, 6)
