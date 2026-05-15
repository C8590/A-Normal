# Factor Spec

## Purpose

`factor_daily` is a daily research table of explainable price, trend, liquidity, volatility, drawdown, and limit-price factors. It is not a stock score, signal, forecast, or investment recommendation.

All calculations use only local CSV data from `trade_date` and earlier. No external APIs, web scraping, broker interfaces, or live trading functions are used.

## Command

```bash
python -m ashare_alpha compute-factors --date 2026-03-20
python -m ashare_alpha compute-factors --date 2026-03-20 --format json
python -m ashare_alpha compute-factors --date 2026-03-20 --output outputs/factors/test.csv
```

Default CSV output:

```text
outputs/factors/factor_daily_YYYY-MM-DD.csv
```

## Fields

- Latest bar: `latest_close`, `latest_open`, `latest_high`, `latest_low`, `latest_amount`, `latest_turnover_rate`
- Returns and trend: `return_1d`, `momentum_5d`, `momentum_20d`, `momentum_60d`, `ma20`, `ma60`, `close_above_ma20`, `close_above_ma60`
- Volatility and drawdown: `volatility_20d`, `max_drawdown_20d`
- Liquidity: `amount_mean_20d`, `turnover_mean_20d`
- Limit statistics: `limit_up_recent_count`, `limit_down_recent_count`
- Computability: `trading_days_used`, `is_computable`, `missing_reasons`, `missing_reason_text`

## Formulas

- `return_1d = close_t / close_t_minus_1 - 1`
- `momentum_Nd = close_t / close_t_minus_N - 1`
- `ma_N = average(close over latest N trading days)`
- `close_above_ma_N = close_t > ma_N`
- `volatility_20d = population_std(latest 20 daily returns, ddof=0)`
- `max_drawdown_20d = min(close_i / running_max_i - 1 over latest 20 closes)`
- `amount_mean_20d = average(amount over latest 20 trading days)`
- `turnover_mean_20d = average(non-missing turnover_rate over latest 20 trading days)`
- `limit_up_recent_count`: count bars where `close >= limit_up - price_tick / 2`
- `limit_down_recent_count`: count bars where `close <= limit_down + price_tick / 2`

Windows come from `configs/ashare_alpha/factors.yaml`; `price_tick` comes from `configs/ashare_alpha/trading_rules.yaml`.

## Missing Reasons

- `NO_BARS`: 没有任何历史日线数据
- `NO_LATEST_BAR_ON_DATE`: 目标交易日没有日线数据
- `NOT_TRADING_ON_DATE`: 目标交易日未交易，无法计算当日因子
- `INSUFFICIENT_HISTORY`: 历史交易日数量不足，无法计算完整因子
- `INSUFFICIENT_MOMENTUM_WINDOW`: 历史交易日数量不足，无法计算动量因子
- `INSUFFICIENT_VOLATILITY_WINDOW`: 历史交易日数量不足，无法计算波动因子
- `INSUFFICIENT_LIQUIDITY_WINDOW`: 历史交易日数量不足，无法计算流动性因子
- `INVALID_PRICE_DATA`: 价格数据异常
