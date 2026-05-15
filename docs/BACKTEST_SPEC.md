# Backtest Spec

The backtest engine is an offline research simulator. It uses `generate-signals` logic to create historical research signals, then simulates execution with A-share trading constraints. It does not connect to brokers and does not submit real orders.

## CLI

```bash
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --output-dir outputs/backtests/test
```

Default output:

```text
outputs/backtests/backtest_START_END/
  trades.csv
  daily_equity.csv
  metrics.json
  summary.md
```

## Signal and Execution Timing

The MVP uses:

- `signal_timing: after_close`
- `execution_price: next_open`

On each rebalance decision date, signals are generated using data available on or before that date. Orders are queued and simulated on the next trading date at the next open. The engine must not use data after `decision_date` to generate the signal.

## Cost Model

Costs come from `fees.yaml` and `backtest.yaml`:

- Commission: `gross_value * commission_rate`
- Minimum commission: `min_commission`
- Stamp tax: sell side only
- Transfer fee: buy and sell side
- Slippage: `backtest.execution.slippage_bps` if set, otherwise `fees.slippage_bps`
- Price tick: `trading_rules.price_tick`

BUY slippage moves price up and rounds up to the configured tick. SELL slippage moves price down and rounds down to the configured tick.

## Trading Constraints

The simulator supports:

- T+1: shares bought today cannot be sold today
- 100-share lot sizing from `trading_rules.lot_size`
- 0.01 CNY price tick from `trading_rules.price_tick`
- no trading when suspended or non-trading
- limit-up buy failure
- limit-down sell failure
- cash constraints
- position constraints
- no short selling
- no leverage

All orders are simulated orders. Rejected simulated orders include human-readable rejection reasons.

## Rebalance Logic

Rebalance frequency comes from `backtest.rebalance_frequency`:

- `daily`: every trading date
- `weekly`: each natural week's last trading date
- `monthly`: each calendar month's last trading date

BUY signals target their research target weight. Held stocks that are no longer BUY can be reduced to zero when `sell_when_signal_not_buy=true`. Held stocks that become BLOCK can be reduced to zero when `exit_on_block=true`.

The engine submits sells before buys on each execution date.

## Metrics

`metrics.json` contains:

- `total_return`: `final_equity / initial_cash - 1`
- `annualized_return`: annualized by `metrics.annualization_days`
- `max_drawdown`: minimum daily equity drawdown from running peak
- `sharpe`: daily-return Sharpe using population standard deviation
- `win_rate`: based on filled SELL trades with realized PnL
- `turnover`: filled gross traded value divided by average daily equity
- `trade_count`
- `filled_trade_count`
- `rejected_trade_count`
- `average_holding_days`

## Boundaries

The backtest is only for research. It is not investment advice, does not guarantee returns, does not call external APIs, does not scrape websites, does not connect to brokers, and does not place orders.
