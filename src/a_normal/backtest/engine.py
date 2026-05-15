from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt
from statistics import fmean, pstdev

from a_normal.backtest.costs import CostModel
from a_normal.backtest.models import BacktestResult, DailyNav, Position, TradeLog
from a_normal.config import FeesConfig, TradingRulesConfig, load_config
from a_normal.data import DailyBar
from a_normal.data.models import _validate_date_format
from a_normal.signals import SignalDaily


class BacktestEngine:
    def __init__(
        self,
        initial_cash: float = 10_000,
        trading_rules: TradingRulesConfig | None = None,
        fees: FeesConfig | None = None,
    ) -> None:
        app_config = load_config()
        self.initial_cash = initial_cash
        self.trading_rules = trading_rules or app_config.trading_rules
        self.fees = fees or app_config.fees
        self.cost_model = CostModel(self.fees, self.trading_rules)

    def run(self, daily_bars: list[DailyBar], signals: list[SignalDaily]) -> BacktestResult:
        bars_by_date = self._bars_by_date(daily_bars)
        signals_by_date = self._signals_by_date(signals)
        trading_dates = sorted(set(bars_by_date) | set(signals_by_date))
        cash = float(self.initial_cash)
        positions: dict[str, Position] = {}
        trades: list[TradeLog] = []
        daily_nav: list[DailyNav] = []

        for trade_date in trading_dates:
            bars = bars_by_date.get(trade_date, {})
            equity_before = self._total_equity(cash, positions, bars)
            for signal in self._ordered_signals(signals_by_date.get(trade_date, [])):
                bar = bars.get(signal.ts_code)
                if bar is None or not self._can_trade_bar(bar):
                    continue
                if signal.signal in {"SELL", "BLOCK"}:
                    cash = self._sell_to_target(signal, bar, trade_date, cash, positions, trades, target_weight=0.0)
                elif signal.signal in {"BUY", "HOLD"}:
                    target_weight = signal.target_weight if signal.signal == "BUY" else min(signal.target_weight, 1.0)
                    cash = self._rebalance_to_target(signal, bar, trade_date, cash, positions, trades, equity_before, target_weight)

            total_equity = self._total_equity(cash, positions, bars)
            market_value = round(total_equity - cash, 6)
            daily_nav.append(
                DailyNav(
                    trade_date=trade_date,
                    cash=round(cash, 6),
                    market_value=market_value,
                    total_equity=round(total_equity, 6),
                    nav=round(total_equity / self.initial_cash, 10),
                    positions={code: position.shares for code, position in positions.items() if position.shares > 0},
                )
            )

        metrics = self._metrics(daily_nav, trades)
        final_equity = daily_nav[-1].total_equity if daily_nav else self.initial_cash
        return BacktestResult(
            initial_cash=self.initial_cash,
            final_equity=final_equity,
            daily_nav=tuple(daily_nav),
            trades=tuple(trades),
            metrics=metrics,
        )

    def _rebalance_to_target(
        self,
        signal: SignalDaily,
        bar: DailyBar,
        trade_date: date,
        cash: float,
        positions: dict[str, Position],
        trades: list[TradeLog],
        total_equity: float,
        target_weight: float,
    ) -> float:
        position = positions.get(signal.ts_code)
        current_shares = position.shares if position else 0
        current_value = current_shares * bar.close
        target_value = total_equity * target_weight
        if target_value <= current_value:
            return cash
        if self._is_limit_up(signal.ts_code, bar, trade_date):
            return cash
        budget = min(cash, target_value - current_value)
        shares = self._affordable_lot_shares(bar.close, budget)
        if shares <= 0:
            return cash
        cost = self.cost_model.calculate(bar.close, shares, "BUY")
        cash -= cost.gross_amount + cost.total_cost
        previous_cost = (position.average_cost * current_shares) if position else 0.0
        new_shares = current_shares + shares
        positions[signal.ts_code] = Position(
            ts_code=signal.ts_code,
            shares=new_shares,
            average_cost=round((previous_cost + cost.gross_amount) / new_shares, 6),
            last_buy_date=trade_date,
        )
        trades.append(self._trade_log(trade_date, signal.ts_code, "BUY", shares, cost, cash, signal.reason))
        return cash

    def _sell_to_target(
        self,
        signal: SignalDaily,
        bar: DailyBar,
        trade_date: date,
        cash: float,
        positions: dict[str, Position],
        trades: list[TradeLog],
        target_weight: float,
    ) -> float:
        position = positions.get(signal.ts_code)
        if position is None or position.shares <= 0:
            return cash
        if self.trading_rules.t_plus_one and position.last_buy_date is not None and trade_date <= position.last_buy_date:
            return cash
        if self._is_limit_down(signal.ts_code, bar, trade_date):
            return cash
        target_shares = int((target_weight * self.initial_cash) // (bar.close * self.trading_rules.lot_size)) * self.trading_rules.lot_size
        shares = max(0, position.shares - target_shares)
        shares = (shares // self.trading_rules.lot_size) * self.trading_rules.lot_size
        if shares <= 0:
            return cash
        cost = self.cost_model.calculate(bar.close, shares, "SELL")
        cash += cost.gross_amount - cost.total_cost
        position.shares -= shares
        if position.shares == 0:
            positions.pop(signal.ts_code, None)
        trades.append(self._trade_log(trade_date, signal.ts_code, "SELL", shares, cost, cash, signal.reason))
        return cash

    def _affordable_lot_shares(self, price: float, budget: float) -> int:
        lot_size = self.trading_rules.lot_size
        lots = int(budget // (price * lot_size))
        while lots > 0:
            shares = lots * lot_size
            cost = self.cost_model.calculate(price, shares, "BUY")
            if cost.gross_amount + cost.total_cost <= budget + 1e-9:
                return shares
            lots -= 1
        return 0

    def _can_trade_bar(self, bar: DailyBar) -> bool:
        return not bar.is_suspended and bar.volume > 0 and bar.close > 0

    def _is_limit_up(self, ts_code: str, bar: DailyBar, trade_date: date) -> bool:
        return self._pct_change_from_previous(ts_code, bar, trade_date) >= self.trading_rules.normal_limit_pct - 1e-10

    def _is_limit_down(self, ts_code: str, bar: DailyBar, trade_date: date) -> bool:
        return self._pct_change_from_previous(ts_code, bar, trade_date) <= -self.trading_rules.normal_limit_pct + 1e-10

    def _pct_change_from_previous(self, ts_code: str, bar: DailyBar, trade_date: date) -> float:
        previous = self._previous_close.get((ts_code, trade_date))
        if previous is None or previous <= 0:
            return 0.0
        return bar.close / previous - 1

    def _bars_by_date(self, daily_bars: list[DailyBar]) -> dict[date, dict[str, DailyBar]]:
        by_code = defaultdict(list)
        for bar in daily_bars:
            by_code[bar.stock_code].append(bar)
        self._previous_close: dict[tuple[str, date], float] = {}
        result: dict[date, dict[str, DailyBar]] = defaultdict(dict)
        for ts_code, bars in by_code.items():
            sorted_bars = sorted(bars, key=lambda item: item.trade_date)
            previous_close = None
            for bar in sorted_bars:
                if previous_close is not None:
                    self._previous_close[(ts_code, bar.trade_date)] = previous_close
                previous_close = bar.close
                result[bar.trade_date][ts_code] = bar
        return dict(result)

    def _signals_by_date(self, signals: list[SignalDaily]) -> dict[date, list[SignalDaily]]:
        result: dict[date, list[SignalDaily]] = defaultdict(list)
        for signal in signals:
            result[signal.trade_date].append(signal)
        return result

    def _ordered_signals(self, signals: list[SignalDaily]) -> list[SignalDaily]:
        priority = {"SELL": 0, "BLOCK": 0, "BUY": 1, "HOLD": 1, "WATCH": 2}
        return sorted(signals, key=lambda item: (priority.get(item.signal, 9), item.ts_code))

    def _total_equity(self, cash: float, positions: dict[str, Position], bars: dict[str, DailyBar]) -> float:
        market_value = 0.0
        for ts_code, position in positions.items():
            bar = bars.get(ts_code)
            market_value += position.shares * (bar.close if bar is not None else position.average_cost)
        return round(cash + market_value, 6)

    def _trade_log(self, trade_date: date, ts_code: str, side, shares: int, cost, cash: float, reason: str) -> TradeLog:
        return TradeLog(
            trade_date=trade_date,
            ts_code=ts_code,
            side=side,
            price=cost.execution_price,
            shares=shares,
            gross_amount=cost.gross_amount,
            commission=cost.commission,
            stamp_tax=cost.stamp_tax,
            total_cost=cost.total_cost,
            cash_after=round(cash, 6),
            reason=reason,
        )

    def _metrics(self, daily_nav: list[DailyNav], trades: list[TradeLog]) -> dict[str, float]:
        if not daily_nav:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe": 0.0,
                "win_rate": 0.0,
                "turnover": 0.0,
                "trade_count": 0.0,
                "average_holding_days": 0.0,
            }
        navs = [item.nav for item in daily_nav]
        total_return = navs[-1] - 1
        periods = max(1, len(navs))
        annualized_return = (navs[-1] ** (252 / periods) - 1) if navs[-1] > 0 else -1.0
        returns = [current / previous - 1 for previous, current in zip(navs, navs[1:]) if previous > 0]
        sharpe = 0.0
        if len(returns) > 1 and pstdev(returns) > 0:
            sharpe = fmean(returns) / pstdev(returns) * sqrt(252)
        turnover = sum(trade.gross_amount for trade in trades) / max(self.initial_cash, 1)
        return {
            "total_return": round(total_return, 10),
            "annualized_return": round(annualized_return, 10),
            "max_drawdown": round(self._max_drawdown(navs), 10),
            "sharpe": round(sharpe, 10),
            "win_rate": round(self._win_rate(trades), 10),
            "turnover": round(turnover, 10),
            "trade_count": float(len(trades)),
            "average_holding_days": round(self._average_holding_days(trades), 10),
        }

    def _max_drawdown(self, navs: list[float]) -> float:
        peak = navs[0]
        max_drawdown = 0.0
        for nav in navs:
            peak = max(peak, nav)
            if peak > 0:
                max_drawdown = min(max_drawdown, nav / peak - 1)
        return max_drawdown

    def _win_rate(self, trades: list[TradeLog]) -> float:
        buys: dict[str, list[TradeLog]] = defaultdict(list)
        wins = 0
        sells = 0
        for trade in trades:
            if trade.side == "BUY":
                buys[trade.ts_code].append(trade)
            elif trade.side == "SELL" and buys[trade.ts_code]:
                buy = buys[trade.ts_code].pop(0)
                sells += 1
                if trade.price > buy.price:
                    wins += 1
        return wins / sells if sells else 0.0

    def _average_holding_days(self, trades: list[TradeLog]) -> float:
        buys: dict[str, list[TradeLog]] = defaultdict(list)
        holding_days = []
        for trade in trades:
            if trade.side == "BUY":
                buys[trade.ts_code].append(trade)
            elif trade.side == "SELL" and buys[trade.ts_code]:
                buy = buys[trade.ts_code].pop(0)
                holding_days.append((trade.trade_date - buy.trade_date).days)
        return fmean(holding_days) if holding_days else 0.0


def run_backtest(
    daily_bars: list[DailyBar],
    signals: list[SignalDaily],
    initial_cash: float = 10_000,
    trading_rules: TradingRulesConfig | None = None,
    fees: FeesConfig | None = None,
) -> BacktestResult:
    return BacktestEngine(initial_cash=initial_cash, trading_rules=trading_rules, fees=fees).run(daily_bars, signals)
