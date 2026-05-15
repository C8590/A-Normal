# Signal Daily Spec

`signal_daily` is the daily research signal table. It combines:

- `universe_daily`
- `factor_daily`
- `event_daily`
- `financial_summary`

The output includes component scores, a final `stock_score`, risk level, BUY / WATCH / BLOCK label, research-only target weight and shares, and Chinese reasons.

This is not investment advice, does not guarantee returns, does not connect to brokers, and does not submit orders.

## CLI

```bash
python -m ashare_alpha generate-signals --date 2026-03-20
python -m ashare_alpha generate-signals --date 2026-03-20 --format json
python -m ashare_alpha generate-signals --date 2026-03-20 --output outputs/signals/test.csv
```

Defaults:

- data directory: `data/sample/ashare_alpha`
- config directory: `configs/ashare_alpha`
- output: `outputs/signals/signal_daily_YYYY-MM-DD.csv`

The command validates local CSV data, builds universe, factor, and event records internally, then writes the signal CSV.

## Component Scores

Market regime uses the cross-section of allowed and computable stocks:

- `strong`: most stocks are above moving averages and 20-day momentum is positive
- `neutral`: breadth is acceptable
- `weak`: breadth is weak
- `risk`: breadth is very weak and 20-day momentum is negative

Industry strength ranks each industry by average 20-day momentum. Missing or undersized industries receive a neutral score of 50.

Trend momentum uses 5-day, 20-day, and 60-day momentum plus MA20 / MA60 position.

Fundamental quality uses only financial summaries with `publish_date <= trade_date`. Future financial data is ignored. The latest published row per stock is used.

Event component maps event score into `[0, 100]`:

```text
event_component_score = clamp(50 + event_score / 2, 0, 100)
```

Volatility control rewards lower volatility and deducts for high volatility, large drawdowns, and recent limit-down counts.

## Formula

Weights come from `configs/ashare_alpha/scoring.yaml`:

```text
raw_score =
  market_regime_score * weights.market_regime
+ industry_strength_score * weights.industry_strength
+ trend_momentum_score * weights.trend_momentum
+ fundamental_quality_score * weights.fundamental_quality
+ liquidity_score * weights.liquidity
+ event_component_score * weights.event
+ volatility_control_score * weights.volatility_control

stock_score = clamp(raw_score - risk_penalty_score, 0, 100)
```

All component scores are saved in `signal_daily`; the final score is never the only output.

## Risk Penalty

Risk penalty combines:

- universe risk score
- event risk score
- low liquidity
- high volatility
- recent limit-down count
- financial risk reasons such as high debt, high goodwill, profit decline, or poor operating cash flow

Risk levels use `risk_level_thresholds` from `scoring.yaml`:

- `high`: `risk_penalty_score >= high`
- `medium`: `risk_penalty_score >= medium`
- otherwise `low`

If `event_risk_score` reaches the high-risk threshold, the signal risk level is at least `high`.

## Signal Meanings

`BUY` means the stock passed the research filters, is not blocked by event or risk rules, reached the configured buy threshold, and received a research-only target position.

`WATCH` means the stock is not blocked but does not currently qualify for BUY, or it was downgraded by market risk, position count, invalid price, or minimum position value constraints.

`BLOCK` means the stock is excluded by the universe, blocked by announcement events, or has high risk.

No SELL signal is generated in this MVP because there is no holdings input. SELL belongs in a future portfolio or backtest module.

## Position Sizing

Position sizing reads:

- `backtest.initial_cash`
- `backtest.max_positions`
- `backtest.max_position_weight`
- `backtest.min_position_value`
- `trading_rules.lot_size`
- `scoring.position_sizing`

Target shares are rounded down to full lots. If the estimated value is below `min_position_value`, the record is downgraded to WATCH.
