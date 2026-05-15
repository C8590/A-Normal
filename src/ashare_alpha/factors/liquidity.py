from __future__ import annotations

from ashare_alpha.data import DailyBar


def amount_mean(bars: list[DailyBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    return sum(bar.amount for bar in bars[-window:]) / window


def turnover_mean(bars: list[DailyBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    values = [bar.turnover_rate for bar in bars[-window:] if bar.turnover_rate is not None]
    if not values:
        return None
    return sum(values) / len(values)
