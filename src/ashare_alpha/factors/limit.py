from __future__ import annotations

from ashare_alpha.data import DailyBar


def limit_up_count(bars: list[DailyBar], window: int, price_tick: float) -> int:
    tolerance = price_tick / 2
    return sum(1 for bar in bars[-window:] if bar.limit_up is not None and bar.close >= bar.limit_up - tolerance)


def limit_down_count(bars: list[DailyBar], window: int, price_tick: float) -> int:
    tolerance = price_tick / 2
    return sum(1 for bar in bars[-window:] if bar.limit_down is not None and bar.close <= bar.limit_down + tolerance)
