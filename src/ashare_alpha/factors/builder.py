from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import DailyBar, StockMaster
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord
from ashare_alpha.factors.limit import limit_down_count, limit_up_count
from ashare_alpha.factors.liquidity import amount_mean, turnover_mean
from ashare_alpha.factors.models import FactorDailyRecord, FactorMissingReason, join_missing_reason_text
from ashare_alpha.factors.price import latest_price_fields, momentum, moving_average, simple_return
from ashare_alpha.factors.price_source import PriceBarRecord, build_price_bars
from ashare_alpha.factors.volatility import max_drawdown, volatility


class FactorBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        daily_bars: list[DailyBar],
        stock_master: list[StockMaster] | None = None,
        price_source: str = "raw",
        adjustment_factors: list[AdjustmentFactorRecord] | None = None,
        corporate_actions: list[CorporateActionRecord] | None = None,
    ) -> None:
        if price_source not in config.factors.price_source.allowed:
            raise ValueError(f"price_source must be one of: {', '.join(config.factors.price_source.allowed)}")
        self.config = config
        self.stock_master = stock_master
        self.price_source = price_source
        self._daily_bars = daily_bars
        self._adjustment_factors = adjustment_factors
        self._corporate_actions = corporate_actions
        self._raw_bars_by_code = _group_daily_bars(daily_bars)
        self._raw_price_bars_by_code = _group_price_bars(build_price_bars(daily_bars, None, None, "raw"))

    def build_for_date(self, trade_date: date) -> list[FactorDailyRecord]:
        codes = self._target_codes()
        price_bars_by_code = self._price_bars_by_code_for_date(trade_date)
        return [self._build_record(ts_code, trade_date, price_bars_by_code) for ts_code in sorted(codes)]

    def _target_codes(self) -> set[str]:
        if self.stock_master is not None:
            return {stock.ts_code for stock in self.stock_master}
        return set(self._raw_bars_by_code)

    def _price_bars_by_code_for_date(self, trade_date: date) -> dict[str, list[PriceBarRecord]]:
        if self.price_source == "raw":
            return self._raw_price_bars_by_code
        return _group_price_bars(
            build_price_bars(
                daily_bars=self._daily_bars,
                adjustment_factors=self._adjustment_factors,
                corporate_actions=self._corporate_actions,
                price_source=self.price_source,
                end_date=trade_date,
            )
        )

    def _build_record(
        self,
        ts_code: str,
        trade_date: date,
        price_bars_by_code: dict[str, list[PriceBarRecord]],
    ) -> FactorDailyRecord:
        raw_bars = self._raw_bars_by_code.get(ts_code, [])
        price_bars = price_bars_by_code.get(ts_code, [])
        historical_raw_bars = [bar for bar in raw_bars if bar.trade_date <= trade_date]
        historical_price_bars = [bar for bar in price_bars if bar.trade_date <= trade_date]
        latest_raw_bar = next((bar for bar in reversed(historical_raw_bars) if bar.trade_date == trade_date), None)
        latest_price_bar = next((bar for bar in reversed(historical_price_bars) if bar.trade_date == trade_date), None)
        raw_trading_bars = [bar for bar in historical_raw_bars if bar.is_trading]
        price_trading_bars = [bar for bar in historical_price_bars if bar.is_trading and bar.close is not None]
        reasons = self._missing_reasons(
            raw_bars,
            latest_raw_bar,
            latest_price_bar,
            historical_price_bars,
            price_trading_bars,
            raw_trading_bars,
        )
        closes = [bar.close for bar in price_trading_bars if bar.close is not None]

        factor_values = self._calculate_factor_values(latest_price_bar, raw_trading_bars, closes)
        unique_reasons = _deduplicate_reasons(reasons)
        adjusted_quality_flags = _adjusted_quality_flags(historical_price_bars)
        return FactorDailyRecord(
            trade_date=trade_date,
            ts_code=ts_code,
            **factor_values,
            trading_days_used=len(price_trading_bars),
            is_computable=not unique_reasons,
            missing_reasons=[reason.value for reason in unique_reasons],
            missing_reason_text=join_missing_reason_text(unique_reasons),
            price_source=self.price_source,
            adjusted_used=self.price_source != "raw",
            adjusted_quality_flags=adjusted_quality_flags,
            adjusted_quality_reason=_adjusted_quality_reason(historical_price_bars),
        )

    def _missing_reasons(
        self,
        all_bars: list[DailyBar],
        latest_bar: DailyBar | None,
        latest_price_bar: PriceBarRecord | None,
        historical_price_bars: list[PriceBarRecord],
        price_trading_bars: list[PriceBarRecord],
        raw_trading_bars: list[DailyBar],
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
        if len(price_trading_bars) < required_min_bars:
            reasons.append(FactorMissingReason.INSUFFICIENT_HISTORY)
        if len(price_trading_bars) < max(factors_config.momentum_windows) + 1:
            reasons.append(FactorMissingReason.INSUFFICIENT_MOMENTUM_WINDOW)
        if len(price_trading_bars) < factors_config.volatility_window + 1:
            reasons.append(FactorMissingReason.INSUFFICIENT_VOLATILITY_WINDOW)
        if len(raw_trading_bars) < factors_config.liquidity_window:
            reasons.append(FactorMissingReason.INSUFFICIENT_LIQUIDITY_WINDOW)
        if any(bar.close is None or bar.close <= 0 for bar in price_trading_bars):
            reasons.append(FactorMissingReason.INVALID_PRICE_DATA)
        if self.price_source != "raw":
            reasons.extend(_adjusted_missing_reasons(latest_price_bar, historical_price_bars))
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
        latest_bar: PriceBarRecord | None,
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


def _group_price_bars(price_bars: list[PriceBarRecord]) -> dict[str, list[PriceBarRecord]]:
    grouped: dict[str, list[PriceBarRecord]] = defaultdict(list)
    for bar in price_bars:
        grouped[bar.ts_code].append(bar)
    for rows in grouped.values():
        rows.sort(key=lambda bar: bar.trade_date)
    return grouped


def _adjusted_missing_reasons(
    latest_price_bar: PriceBarRecord | None,
    historical_price_bars: list[PriceBarRecord],
) -> list[FactorMissingReason]:
    reasons: list[FactorMissingReason] = []
    if latest_price_bar is None or not latest_price_bar.has_complete_price:
        reasons.append(FactorMissingReason.ADJUSTED_PRICE_UNAVAILABLE)
    flags = _adjusted_quality_flags(historical_price_bars)
    if "MISSING_ADJ_FACTOR" in flags or "MISSING_BASE_FACTOR" in flags:
        reasons.append(FactorMissingReason.ADJUSTED_FACTOR_MISSING)
    if "INVALID_ADJUSTED_PRICE" in flags or any(not bar.has_complete_price for bar in historical_price_bars):
        reasons.append(FactorMissingReason.ADJUSTED_PRICE_INVALID)
    return reasons


def _adjusted_quality_flags(price_bars: list[PriceBarRecord]) -> list[str]:
    flags: set[str] = set()
    for bar in price_bars:
        flags.update(bar.adjusted_quality_flags)
    return sorted(flags)


def _adjusted_quality_reason(price_bars: list[PriceBarRecord]) -> str | None:
    reasons = sorted({bar.adjusted_quality_reason for bar in price_bars if bar.adjusted_quality_reason})
    return "；".join(reasons) if reasons else None


def _deduplicate_reasons(reasons: list[FactorMissingReason]) -> list[FactorMissingReason]:
    seen: set[FactorMissingReason] = set()
    result: list[FactorMissingReason] = []
    for reason in reasons:
        if reason not in seen:
            result.append(reason)
            seen.add(reason)
    return result
