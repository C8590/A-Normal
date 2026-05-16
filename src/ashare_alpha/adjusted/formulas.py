from __future__ import annotations


def compute_adjustment_ratio(adj_factor: float, base_adj_factor: float) -> float:
    if adj_factor <= 0:
        raise ValueError("adj_factor must be greater than zero")
    if base_adj_factor <= 0:
        raise ValueError("base_adj_factor must be greater than zero")
    return adj_factor / base_adj_factor


def adjust_price(raw_price: float, adjustment_ratio: float) -> float:
    return raw_price * adjustment_ratio


def compute_return(current_close: float | None, previous_close: float | None) -> float | None:
    if current_close is None or previous_close is None or previous_close <= 0:
        return None
    return current_close / previous_close - 1
