from __future__ import annotations

from ashare_alpha.data import DailyBar


def simple_return(current_close: float, previous_close: float) -> float | None:
    if previous_close <= 0:
        return None
    return current_close / previous_close - 1


def momentum(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    return simple_return(closes[-1], closes[-window - 1])


def moving_average(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def latest_price_fields(latest_bar: DailyBar | None) -> dict[str, float | None]:
    if latest_bar is None:
        return {
            "latest_close": None,
            "latest_open": None,
            "latest_high": None,
            "latest_low": None,
            "latest_amount": None,
            "latest_turnover_rate": None,
        }
    return {
        "latest_close": latest_bar.close,
        "latest_open": latest_bar.open,
        "latest_high": latest_bar.high,
        "latest_low": latest_bar.low,
        "latest_amount": latest_bar.amount,
        "latest_turnover_rate": latest_bar.turnover_rate,
    }
