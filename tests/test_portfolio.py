from __future__ import annotations

from datetime import date

import pytest

from ashare_alpha.backtest import Portfolio
from ashare_alpha.config import load_project_config


def test_buy_reduces_cash_and_adds_position() -> None:
    portfolio = _portfolio()

    portfolio.buy("600001.SH", 100, 10.01, date(2026, 3, 20), -1001)

    assert portfolio.cash == 8999
    assert portfolio.get_total_shares("600001.SH") == 100


def test_t_plus_one_same_day_shares_are_not_available() -> None:
    portfolio = _portfolio()
    portfolio.buy("600001.SH", 100, 10, date(2026, 3, 20), -1000)

    assert portfolio.get_available_shares("600001.SH", date(2026, 3, 20)) == 0


def test_t_plus_one_next_day_shares_are_available() -> None:
    portfolio = _portfolio()
    portfolio.buy("600001.SH", 100, 10, date(2026, 3, 20), -1000)

    assert portfolio.get_available_shares("600001.SH", date(2026, 3, 21)) == 100


def test_sell_cannot_exceed_available_shares() -> None:
    portfolio = _portfolio()
    portfolio.buy("600001.SH", 100, 10, date(2026, 3, 20), -1000)

    with pytest.raises(ValueError, match="available"):
        portfolio.sell("600001.SH", 200, date(2026, 3, 21), 2000)


def test_fifo_sell_calculates_realized_pnl() -> None:
    portfolio = _portfolio()
    portfolio.buy("600001.SH", 100, 10, date(2026, 3, 18), -1000)
    portfolio.buy("600001.SH", 100, 12, date(2026, 3, 19), -1200)

    realized_pnl, holding_days = portfolio.sell("600001.SH", 100, date(2026, 3, 20), 1100)

    assert realized_pnl == 100
    assert holding_days == 2
    assert portfolio.get_total_shares("600001.SH") == 100


def test_shares_must_be_lot_multiple() -> None:
    with pytest.raises(ValueError, match="lot_size"):
        _portfolio().buy("600001.SH", 50, 10, date(2026, 3, 20), -500)


def test_buy_cannot_make_cash_negative() -> None:
    with pytest.raises(ValueError, match="cash negative"):
        _portfolio().buy("600001.SH", 100, 10, date(2026, 3, 20), -20000)


def _portfolio() -> Portfolio:
    return Portfolio(10_000, load_project_config().trading_rules)
