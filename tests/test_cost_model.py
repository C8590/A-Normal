from __future__ import annotations

from a_normal.backtest import CostModel
from a_normal.config import FeesConfig, TradingRulesConfig
from ashare_alpha.backtest import CostModel as AShareCostModel
from ashare_alpha.config import load_project_config


def test_cost_model_applies_tick_slippage_commission_and_stamp_tax():
    model = CostModel(
        fees=FeesConfig(commission_rate=0.00005, min_commission=0.1, stamp_tax_rate_on_sell=0.0005, slippage_bps=5),
        trading_rules=TradingRulesConfig(price_tick=0.01),
    )

    buy = model.calculate(price=10.003, shares=100, side="BUY")
    sell = model.calculate(price=10.003, shares=100, side="SELL")

    assert buy.execution_price == 10.01
    assert buy.gross_amount == 1001
    assert buy.commission == 0.1
    assert buy.stamp_tax == 0
    assert buy.total_cost == 0.1
    assert sell.execution_price == 10.0
    assert sell.commission == 0.1
    assert sell.stamp_tax == 0.5
    assert sell.total_cost == 0.6


def test_cost_model_uses_rate_commission_when_above_minimum():
    model = CostModel(
        fees=FeesConfig(commission_rate=0.00005, min_commission=0.1, stamp_tax_rate_on_sell=0.0005, slippage_bps=0),
        trading_rules=TradingRulesConfig(price_tick=0.01),
    )

    cost = model.calculate(price=100, shares=10000, side="BUY")

    assert cost.gross_amount == 1_000_000
    assert cost.commission == 50
    assert cost.total_cost == 50


def test_cost_model_cash_delta_for_buy_and_sell():
    model = CostModel(
        fees=FeesConfig(commission_rate=0.00005, min_commission=0.1, stamp_tax_rate_on_sell=0.0005, slippage_bps=0),
        trading_rules=TradingRulesConfig(price_tick=0.01),
    )

    assert model.cash_delta(price=10, shares=100, side="BUY") == -1000.1
    assert model.cash_delta(price=10, shares=100, side="SELL") == 999.4


def test_ashare_cost_model_buy_slippage_rounds_up_to_tick():
    model = AShareCostModel(load_project_config())

    assert model.apply_slippage(10.003, "BUY") == 10.01


def test_ashare_cost_model_sell_slippage_rounds_down_to_tick():
    model = AShareCostModel(load_project_config())

    assert model.apply_slippage(10.003, "SELL") == 9.99


def test_ashare_cost_model_uses_rate_commission_when_above_minimum():
    model = AShareCostModel(load_project_config())
    cost = model.calculate_trade_cost("BUY", 100, 10000)

    assert cost.commission == 50


def test_ashare_cost_model_minimum_commission_applies():
    model = AShareCostModel(load_project_config())
    cost = model.calculate_trade_cost("BUY", 10, 100)

    assert cost.commission == 0.1


def test_ashare_cost_model_stamp_tax_only_on_sell():
    model = AShareCostModel(load_project_config())

    assert model.calculate_trade_cost("BUY", 10, 100).stamp_tax == 0
    assert model.calculate_trade_cost("SELL", 10, 100).stamp_tax == 0.5


def test_ashare_cost_model_transfer_fee_applies():
    config = load_project_config()
    config = config.model_copy(update={"fees": config.fees.model_copy(update={"transfer_fee_rate": 0.001})})
    cost = AShareCostModel(config).calculate_trade_cost("BUY", 10, 100)

    assert cost.transfer_fee == 1


def test_ashare_cost_model_cash_changes_have_expected_signs():
    model = AShareCostModel(load_project_config())

    assert model.calculate_trade_cost("BUY", 10, 100).net_cash_change < 0
    assert model.calculate_trade_cost("SELL", 10, 100).net_cash_change > 0
