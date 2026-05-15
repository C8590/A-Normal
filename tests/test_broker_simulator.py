from __future__ import annotations

from datetime import date

from ashare_alpha.backtest import BrokerSimulator, CostModel, Portfolio, SimulatedOrder
from ashare_alpha.config import load_project_config
from tests_support import daily_bar


def test_missing_execution_bar_is_rejected() -> None:
    trade = _broker().execute_order(_order("BUY"), None)

    assert trade.status == "REJECTED"
    assert trade.reject_reason == "执行日无行情数据"


def test_suspended_bar_is_rejected() -> None:
    trade = _broker().execute_order(_order("BUY"), daily_bar(is_trading=False))

    assert trade.status == "REJECTED"
    assert trade.reject_reason == "执行日停牌或未交易"


def test_limit_up_buy_is_rejected() -> None:
    trade = _broker().execute_order(_order("BUY"), daily_bar(open=11.0, high=11.0, close=11.0, limit_up=11.0))

    assert trade.status == "REJECTED"
    assert "涨停" in trade.reject_reason


def test_limit_down_sell_is_rejected() -> None:
    broker = _broker_with_position()
    trade = broker.execute_order(_order("SELL"), daily_bar(open=9.0, low=9.0, close=9.0, limit_down=9.0))

    assert trade.status == "REJECTED"
    assert "跌停" in trade.reject_reason


def test_cash_shortage_buy_is_rejected() -> None:
    trade = _broker().execute_order(_order("BUY", shares=2000), daily_bar(open=10))

    assert trade.status == "REJECTED"
    assert trade.reject_reason == "现金不足"


def test_t_plus_one_shortage_sell_is_rejected() -> None:
    broker = _broker()
    broker.portfolio.buy("600001.SH", 100, 10, date(2026, 3, 20), -1000)

    trade = broker.execute_order(_order("SELL"), daily_bar())

    assert trade.status == "REJECTED"
    assert "T+1" in trade.reject_reason


def test_normal_buy_updates_portfolio() -> None:
    broker = _broker()

    trade = broker.execute_order(_order("BUY"), daily_bar(open=10))

    assert trade.status == "FILLED"
    assert broker.portfolio.get_total_shares("600001.SH") == 100


def test_normal_sell_updates_portfolio_and_realized_pnl() -> None:
    broker = _broker_with_position()

    trade = broker.execute_order(_order("SELL"), daily_bar(open=10.5, high=10.6, close=10.5))

    assert trade.status == "FILLED"
    assert broker.portfolio.get_total_shares("600001.SH") == 0
    assert trade.realized_pnl is not None


def _broker() -> BrokerSimulator:
    config = load_project_config()
    portfolio = Portfolio(config.backtest.initial_cash, config.trading_rules)
    return BrokerSimulator(config, CostModel(config), portfolio)


def _broker_with_position() -> BrokerSimulator:
    broker = _broker()
    broker.portfolio.buy("600001.SH", 100, 10, date(2026, 3, 19), -1000)
    return broker


def _order(side: str, shares: int = 100) -> SimulatedOrder:
    return SimulatedOrder(
        decision_date=date(2026, 3, 19),
        execution_date=date(2026, 3, 20),
        ts_code="600001.SH",
        side=side,
        requested_shares=shares,
        target_weight=0.5 if side == "BUY" else 0,
        reason="模拟测试订单",
    )
