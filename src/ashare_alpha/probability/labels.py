from __future__ import annotations

from collections import defaultdict
from datetime import date

from ashare_alpha.data import DailyBar


def compute_future_return(
    daily_bars: list[DailyBar],
    ts_code: str,
    trade_date: date,
    horizon: int,
) -> float | None:
    """Compute a future return label from trading bars only."""

    if horizon <= 0:
        raise ValueError("horizon must be positive")
    bars = _trading_bars_by_code(daily_bars).get(ts_code, [])
    index_by_date = {bar.trade_date: index for index, bar in enumerate(bars)}
    current_index = index_by_date.get(trade_date)
    if current_index is None:
        return None
    future_index = current_index + horizon
    if future_index >= len(bars):
        return None
    close_t = bars[current_index].close
    future_close = bars[future_index].close
    if close_t <= 0:
        return None
    return future_close / close_t - 1


def make_win_label(future_return: float | None, threshold: float) -> int | None:
    if future_return is None:
        return None
    return 1 if future_return > threshold else 0


def _trading_bars_by_code(daily_bars: list[DailyBar]) -> dict[str, list[DailyBar]]:
    grouped: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in daily_bars:
        if bar.is_trading:
            grouped[bar.ts_code].append(bar)
    for rows in grouped.values():
        rows.sort(key=lambda bar: bar.trade_date)
    return grouped
