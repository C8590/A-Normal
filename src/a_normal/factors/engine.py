from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date
from pathlib import Path
from statistics import fmean, pstdev
from typing import Iterable

from a_normal.config import TradingRulesConfig, load_config
from a_normal.data import DailyBar
from a_normal.data.models import _validate_date_format
from a_normal.factors.models import FactorDaily


FACTOR_CSV_FIELDS = [
    "ts_code",
    "trade_date",
    "close",
    "momentum_5d",
    "momentum_20d",
    "momentum_60d",
    "volatility_20d",
    "max_drawdown_20d",
    "amount_mean_20d",
    "turnover_mean_20d",
    "close_above_ma20",
    "close_above_ma60",
    "limit_up_recent_count",
    "limit_down_recent_count",
]


def build_factor_daily(
    daily_bars: Iterable[DailyBar],
    as_of_date: str | date | None = None,
    trading_rules: TradingRulesConfig | None = None,
) -> list[FactorDaily]:
    """Build per-stock daily factors from validated daily bars.

    Invalid or sparse windows yield ``None`` for the affected factor. A malformed
    individual stock series is skipped for that series only, so one bad symbol
    does not prevent all other factor rows from being produced.
    """

    target_date = _parse_date(as_of_date) if as_of_date is not None else None
    rules = trading_rules or load_config().trading_rules
    grouped: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in daily_bars:
        if target_date is None or bar.trade_date <= target_date:
            grouped[bar.stock_code].append(bar)

    factors: list[FactorDaily] = []
    for stock_code in sorted(grouped):
        bars = sorted(grouped[stock_code], key=lambda item: item.trade_date)
        for index, _bar in enumerate(bars):
            if target_date is not None and bars[index].trade_date != target_date:
                continue
            try:
                factors.append(_build_row(bars, index, rules))
            except (ArithmeticError, ValueError, TypeError):
                continue
    return factors


def save_factor_daily_csv(factors: Iterable[FactorDaily], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FACTOR_CSV_FIELDS)
        writer.writeheader()
        for factor in factors:
            row = factor.model_dump(mode="json")
            writer.writerow({field: _csv_value(row.get(field)) for field in FACTOR_CSV_FIELDS})


def _build_row(bars: list[DailyBar], index: int, rules: TradingRulesConfig) -> FactorDaily:
    current = bars[index]
    closes = [bar.close for bar in bars[: index + 1]]
    amounts = [bar.amount for bar in bars[: index + 1]]
    turnovers = [bar.turnover_rate for bar in bars[: index + 1]]
    returns = _returns(closes)

    return FactorDaily(
        ts_code=current.stock_code,
        trade_date=current.trade_date,
        close=current.close,
        momentum_5d=_momentum(closes, 5),
        momentum_20d=_momentum(closes, 20),
        momentum_60d=_momentum(closes, 60),
        volatility_20d=_volatility(returns, 20),
        max_drawdown_20d=_max_drawdown(closes[-20:]),
        amount_mean_20d=_mean(amounts[-20:]),
        turnover_mean_20d=_mean([item for item in turnovers[-20:] if item is not None]),
        close_above_ma20=_close_above_ma(closes, 20),
        close_above_ma60=_close_above_ma(closes, 60),
        limit_up_recent_count=_limit_count(closes, rules.normal_limit_pct, direction="up"),
        limit_down_recent_count=_limit_count(closes, rules.normal_limit_pct, direction="down"),
    )


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    _validate_date_format(value)
    return date.fromisoformat(value)


def _momentum(closes: list[float], window: int) -> float | None:
    if len(closes) <= window:
        return None
    previous = closes[-window - 1]
    current = closes[-1]
    if previous <= 0:
        return None
    return round(current / previous - 1.0, 10)


def _returns(closes: list[float]) -> list[float]:
    result = []
    for previous, current in zip(closes, closes[1:]):
        if previous <= 0:
            continue
        result.append(current / previous - 1.0)
    return result


def _volatility(returns: list[float], window: int) -> float | None:
    recent_returns = returns[-window:]
    if len(recent_returns) < 2:
        return None
    return round(pstdev(recent_returns), 10)


def _max_drawdown(closes: list[float]) -> float | None:
    if not closes:
        return None
    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        if close > peak:
            peak = close
        if peak <= 0:
            continue
        drawdown = close / peak - 1.0
        max_drawdown = min(max_drawdown, drawdown)
    return round(max_drawdown, 10)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(fmean(values), 10)


def _close_above_ma(closes: list[float], window: int) -> bool | None:
    if len(closes) < window:
        return None
    return closes[-1] > fmean(closes[-window:])


def _limit_count(closes: list[float], limit_pct: float, direction: str, window: int = 20) -> int:
    recent_closes = closes[-(window + 1) :]
    count = 0
    epsilon = 1e-10
    for previous, current in zip(recent_closes, recent_closes[1:]):
        if previous <= 0:
            continue
        pct_change = current / previous - 1.0
        if direction == "up" and pct_change >= limit_pct - epsilon:
            count += 1
        elif direction == "down" and pct_change <= -limit_pct + epsilon:
            count += 1
    return count


def _csv_value(value):
    if value is None:
        return ""
    return value
