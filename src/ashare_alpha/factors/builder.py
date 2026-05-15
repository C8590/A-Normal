from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import DailyBar, StockMaster
from ashare_alpha.factors.limit import limit_down_count, limit_up_count
from ashare_alpha.factors.liquidity import amount_mean, turnover_mean
from ashare_alpha.factors.models import FactorDailyRecord, FactorMissingReason, join_missing_reason_text
from ashare_alpha.factors.price import latest_price_fields, momentum, moving_average, simple_return
from ashare_alpha.factors.volatility import max_drawdown, volatility


class FactorBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        daily_bars: list[DailyBar],
        stock_master: list[StockMaster] | None = None,
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self._bars_by_code = _group_daily_bars(daily_bars)

    def build_for_date(self, trade_date: date) -> list[FactorDailyRecord]:
        codes = self._target_codes()
        return [self._build_record(ts_code, trade_date) for ts_code in sorted(codes)]

    def _target_codes(self) -> set[str]:
        if self.stock_master is not None:
            return {stock.ts_code for stock in self.stock_master}
        return set(self._bars_by_code)

    def _build_record(self, ts_code: str, trade_date: date) -> FactorDailyRecord:
        all_bars = self._bars_by_code.get(ts_code, [])
        historical_bars = [bar for bar in all_bars if bar.trade_date <= trade_date]
        latest_bar = next((bar for bar in reversed(historical_bars) if bar.trade_date == trade_date), None)
        trading_bars = [bar for bar in historical_bars if bar.is_trading]
        reasons = self._missing_reasons(all_bars, latest_bar, trading_bars)
        closes = [bar.close for bar in trading_bars]

        factor_values = self._calculate_factor_values(latest_bar, trading_bars, closes)
        unique_reasons = _deduplicate_reasons(reasons)
        return FactorDailyRecord(
            trade_date=trade_date,
            ts_code=ts_code,
            **factor_values,
            trading_days_used=len(trading_bars),
            is_computable=not unique_reasons,
            missing_reasons=[reason.value for reason in unique_reasons],
            missing_reason_text=join_missing_reason_text(unique_reasons),
        )

    def _missing_reasons(
        self,
        all_bars: list[DailyBar],
        latest_bar: DailyBar | None,
        trading_bars: list[DailyBar],
    ) -> list[FactorMissingReason]:
        reasons: list[FactorMissingReason] = []
        required_min_bars = self._required_min_bars()
        factors_config = self.config.factors

        if not all_bars:
            reasons.append(FactorMissingReason.NO_BARS)
        if latest_bar is None:
            reasons.append(FactorMissingReason.NO_LATEST_BAR_ON_DATE)
        elif not latest_bar.is_trading:
            reasons.append(FactorMissingReason.NOT_TRADING_ON_DATE)
        if len(trading_bars) < required_min_bars:
            reasons.append(FactorMissingReason.INSUFFICIENT_HISTORY)
        if len(trading_bars) < max(factors_config.momentum_windows) + 1:
            reasons.append(FactorMissingReason.INSUFFICIENT_MOMENTUM_WINDOW)
        if len(trading_bars) < factors_config.volatility_window + 1:
            reasons.append(FactorMissingReason.INSUFFICIENT_VOLATILITY_WINDOW)
        if len(trading_bars) < factors_config.liquidity_window:
            reasons.append(FactorMissingReason.INSUFFICIENT_LIQUIDITY_WINDOW)
        if any(bar.close <= 0 for bar in trading_bars):
            reasons.append(FactorMissingReason.INVALID_PRICE_DATA)
        return reasons

    def _required_min_bars(self) -> int:
        factors_config = self.config.factors
        return max(
            max(factors_config.momentum_windows) + 1,
            factors_config.volatility_window + 1,
            factors_config.max_drawdown_window,
            factors_config.liquidity_window,
            max(factors_config.ma_windows),
            factors_config.recent_limit_window,
        )

    def _calculate_factor_values(
        self,
        latest_bar: DailyBar | None,
        trading_bars: list[DailyBar],
        closes: list[float],
    ) -> dict:
        factors_config = self.config.factors
        price_tick = self.config.trading_rules.price_tick
        return_1d = simple_return(closes[-1], closes[-2]) if len(closes) >= 2 else None
        ma20 = moving_average(closes, 20) if 20 in factors_config.ma_windows else None
        ma60 = moving_average(closes, 60) if 60 in factors_config.ma_windows else None
        latest_close = latest_bar.close if latest_bar is not None else None
        return {
            **latest_price_fields(latest_bar),
            "return_1d": return_1d,
            "momentum_5d": momentum(closes, 5) if 5 in factors_config.momentum_windows else None,
            "momentum_20d": momentum(closes, 20) if 20 in factors_config.momentum_windows else None,
            "momentum_60d": momentum(closes, 60) if 60 in factors_config.momentum_windows else None,
            "ma20": ma20,
            "ma60": ma60,
            "close_above_ma20": latest_close > ma20 if latest_close is not None and ma20 is not None else None,
            "close_above_ma60": latest_close > ma60 if latest_close is not None and ma60 is not None else None,
            "volatility_20d": volatility(closes, factors_config.volatility_window),
            "max_drawdown_20d": max_drawdown(closes, factors_config.max_drawdown_window),
            "amount_mean_20d": amount_mean(trading_bars, factors_config.liquidity_window),
            "turnover_mean_20d": turnover_mean(trading_bars, factors_config.liquidity_window),
            "limit_up_recent_count": limit_up_count(trading_bars, factors_config.recent_limit_window, price_tick),
            "limit_down_recent_count": limit_down_count(trading_bars, factors_config.recent_limit_window, price_tick),
        }


def summarize_factors(records: list[FactorDailyRecord]) -> dict:
    reason_counts: Counter[str] = Counter()
    for record in records:
        reason_counts.update(record.missing_reasons)
    return {
        "total": len(records),
        "computable": sum(1 for record in records if record.is_computable),
        "not_computable": sum(1 for record in records if not record.is_computable),
        "missing_reason_counts": dict(sorted(reason_counts.items())),
    }


def _group_daily_bars(daily_bars: list[DailyBar]) -> dict[str, list[DailyBar]]:
    grouped: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in daily_bars:
        grouped[bar.ts_code].append(bar)
    for rows in grouped.values():
        rows.sort(key=lambda bar: bar.trade_date)
    return grouped


def _deduplicate_reasons(reasons: list[FactorMissingReason]) -> list[FactorMissingReason]:
    seen: set[FactorMissingReason] = set()
    result: list[FactorMissingReason] = []
    for reason in reasons:
        if reason not in seen:
            result.append(reason)
            seen.add(reason)
    return result
