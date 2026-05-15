from __future__ import annotations

from datetime import date

from ashare_alpha.config import TradingRulesConfig
from ashare_alpha.backtest.models import PositionLot, PositionSnapshot


class Portfolio:
    def __init__(self, initial_cash: float, trading_rules: TradingRulesConfig) -> None:
        if initial_cash < 0:
            raise ValueError("initial_cash must be non-negative")
        self.cash = initial_cash
        self.trading_rules = trading_rules
        self.lots_by_symbol: dict[str, list[PositionLot]] = {}

    def get_total_shares(self, ts_code: str) -> int:
        return sum(lot.shares for lot in self.lots_by_symbol.get(ts_code, []))

    def get_available_shares(self, ts_code: str, trade_date: date) -> int:
        lots = self.lots_by_symbol.get(ts_code, [])
        if not self.trading_rules.t_plus_one:
            return sum(lot.shares for lot in lots)
        return sum(lot.shares for lot in lots if lot.buy_date < trade_date)

    def buy(self, ts_code: str, shares: int, cost_per_share: float, buy_date: date, cash_change: float) -> None:
        self._validate_lot_shares(shares)
        if self.cash + cash_change < -1e-9:
            raise ValueError("buy would make cash negative")
        if cash_change > 0:
            raise ValueError("buy cash_change must be non-positive")
        self.cash += cash_change
        self.lots_by_symbol.setdefault(ts_code, []).append(
            PositionLot(ts_code=ts_code, shares=shares, cost_per_share=cost_per_share, buy_date=buy_date)
        )

    def sell(self, ts_code: str, shares: int, sell_date: date, net_cash_change: float) -> tuple[float, int]:
        self._validate_lot_shares(shares)
        if shares > self.get_available_shares(ts_code, sell_date):
            raise ValueError("sell shares exceed available shares")
        remaining = shares
        sold_cost = 0.0
        weighted_holding_days = 0
        lots = self.lots_by_symbol.get(ts_code, [])
        for lot in list(lots):
            if remaining <= 0:
                break
            if self.trading_rules.t_plus_one and lot.buy_date >= sell_date:
                continue
            sold = min(remaining, lot.shares)
            lot.shares -= sold
            remaining -= sold
            sold_cost += sold * lot.cost_per_share
            weighted_holding_days += sold * (sell_date - lot.buy_date).days
        self.lots_by_symbol[ts_code] = [lot for lot in lots if lot.shares > 0]
        if not self.lots_by_symbol[ts_code]:
            del self.lots_by_symbol[ts_code]
        self.cash += net_cash_change
        realized_pnl = net_cash_change - sold_cost
        average_holding_days = int(round(weighted_holding_days / shares))
        return realized_pnl, average_holding_days

    def mark_to_market(self, trade_date: date, price_map: dict[str, float]) -> list[PositionSnapshot]:
        snapshots: list[PositionSnapshot] = []
        for ts_code in sorted(self.lots_by_symbol):
            lots = self.lots_by_symbol[ts_code]
            shares = sum(lot.shares for lot in lots)
            total_cost = sum(lot.shares * lot.cost_per_share for lot in lots)
            average_cost = total_cost / shares if shares else None
            price = price_map.get(ts_code)
            market_value = shares * price if price is not None else 0.0
            unrealized_pnl = market_value - total_cost if price is not None else None
            snapshots.append(
                PositionSnapshot(
                    trade_date=trade_date,
                    ts_code=ts_code,
                    shares=shares,
                    available_shares=self.get_available_shares(ts_code, trade_date),
                    market_price=price,
                    market_value=market_value,
                    average_cost=average_cost,
                    unrealized_pnl=unrealized_pnl,
                )
            )
        return snapshots

    def _validate_lot_shares(self, shares: int) -> None:
        if shares <= 0:
            raise ValueError("shares must be greater than 0")
        if shares % self.trading_rules.lot_size != 0:
            raise ValueError("shares must be an integer multiple of lot_size")
