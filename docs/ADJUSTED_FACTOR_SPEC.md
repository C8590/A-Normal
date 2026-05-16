# Adjusted Factor Spec

`factor_daily` can optionally compute price-derived factors from `raw`, `qfq`, or `hfq` price sources. This is for offline research only. It does not change signal generation, backtest execution, broker connectivity, or live trading behavior.

## Why Support Raw, Qfq, And Hfq

Corporate actions can make raw historical prices discontinuous. Optional adjusted price sources make it possible to study whether returns, momentum, moving averages, volatility, and drawdown change when prices are adjusted with locally supplied `adjustment_factor.csv` rows.

## Default Remains Raw

The default is still `raw` for compatibility with the existing MVP workflow:

```bash
python -m ashare_alpha compute-factors --date 2026-03-20
python -m ashare_alpha compute-factors --date 2026-03-20 --price-source raw
```

`run-pipeline` and `run-backtest` defaults are unchanged and continue to use the existing raw factor path unless a future task explicitly changes them.

## Compute Factors

Use `--price-source` to generate a separate adjusted factor file:

```bash
python -m ashare_alpha compute-factors --date 2026-03-20 --price-source qfq
python -m ashare_alpha compute-factors --date 2026-03-20 --price-source hfq
```

Default output names:

- `raw`: `outputs/factors/factor_daily_YYYY-MM-DD.csv`
- `qfq`: `outputs/factors/factor_daily_YYYY-MM-DD_qfq.csv`
- `hfq`: `outputs/factors/factor_daily_YYYY-MM-DD_hfq.csv`

Each `FactorDailyRecord` records `price_source`, `adjusted_used`, `adjusted_quality_flags`, and `adjusted_quality_reason`.

## Compare Price Sources

Compare raw and adjusted factor versions:

```bash
python -m ashare_alpha compare-factor-price-sources --date 2026-03-20 --left raw --right qfq
```

The command writes:

- `factor_price_source_compare.csv`
- `factor_price_source_compare.json`
- `factor_price_source_compare.md`

The comparison aligns by `ts_code` and reports differences for momentum, moving averages, volatility, drawdown, and moving-average crossover booleans.

## Adjusted Price Factors

When `--price-source qfq` or `--price-source hfq` is explicit, adjusted prices are used for:

- `return_1d`
- `momentum_5d`, `momentum_20d`, `momentum_60d`
- `ma20`, `ma60`
- `close_above_ma20`, `close_above_ma60`
- `volatility_20d`
- `max_drawdown_20d`

## Raw Data Factors

These fields remain based on raw `daily_bar.csv` data:

- `amount_mean_20d`
- `turnover_mean_20d`
- `limit_up_recent_count`
- `limit_down_recent_count`

Limit statistics continue to use raw `close`, `limit_up`, and `limit_down`; adjusted prices are not used to judge limit-up or limit-down events.

## Safety Boundary

This feature is only for research comparison. It is not investment advice, does not guarantee returns, does not call external APIs, does not scrape websites, does not connect to brokers, and does not place orders automatically.
