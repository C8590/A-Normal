from __future__ import annotations


def population_std(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return variance**0.5


def daily_returns(closes: list[float]) -> list[float] | None:
    if len(closes) < 2:
        return None
    returns: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        if previous <= 0:
            return None
        returns.append(current / previous - 1)
    return returns


def volatility(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    returns = daily_returns(closes[-(window + 1) :])
    if returns is None:
        return None
    return population_std(returns)


def max_drawdown(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    running_max = closes[-window]
    max_drawdown_value = 0.0
    for close in closes[-window:]:
        running_max = max(running_max, close)
        if running_max <= 0:
            return None
        max_drawdown_value = min(max_drawdown_value, close / running_max - 1)
    return max_drawdown_value
