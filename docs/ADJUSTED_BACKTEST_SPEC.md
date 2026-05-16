# Adjusted Backtest Spec

`run-backtest` supports an optional `--price-source raw/qfq/hfq` for research valuation. The default remains `raw`, so existing `run-backtest` and `run-pipeline` behavior does not change.

## Why This Exists

Raw A-share prices are the only realistic basis for simulated execution constraints. Adjusted prices are useful for research views such as equity-curve valuation across corporate actions and comparing raw versus adjusted valuation sensitivity.

## Price Sources

- `raw`: uses `daily_bar.csv` prices. This is the default.
- `qfq`: uses locally built forward-adjusted prices from `adjustment_factor.csv` and `corporate_action.csv`.
- `hfq`: uses locally built backward-adjusted prices from the same local optional realism files.

No external API, web scraping, broker connection, or live order path is introduced.

## Execution Boundary

Execution remains raw in every mode:

- limit-up buy failure uses raw `open` and raw `limit_up`
- limit-down sell failure uses raw `open` and raw `limit_down`
- suspension checks use raw `is_trading`
- T+1 availability is unchanged
- commissions, stamp tax, transfer fee, slippage, and cash impact use raw execution price

Adjusted price must not be treated as a real tradable execution price.

## Commands

```bash
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --price-source raw
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --price-source qfq
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --price-source hfq
```

Raw outputs keep the existing directory naming:

```text
outputs/backtests/backtest_START_END/
```

Adjusted outputs include the source suffix:

```text
outputs/backtests/backtest_START_END_qfq/
outputs/backtests/backtest_START_END_hfq/
```

## Compare Command

```bash
python -m ashare_alpha compare-backtest-price-sources --start 2026-01-05 --end 2026-03-20 --left raw --right qfq
```

The compare command runs two offline backtests, saves `left/` and `right/` result directories, and writes:

- `backtest_price_source_compare.json`
- `backtest_price_source_compare.md`
- `backtest_price_source_compare.csv`

Reported diffs include total return, annualized return, max drawdown, Sharpe, trade count, and final equity.

## Output Fields

- `metrics.json` includes `price_source`.
- `trades.csv` includes `price_source`, `execution_price_source`, and `valuation_price_source`.
- `daily_equity.csv` includes `price_source` and `valuation_basis`.
- `summary.md` states that raw daily bars remain the execution constraint basis.

If adjusted valuation is unavailable for a held or evaluated symbol, the engine records an explicit warning and falls back to raw close for valuation instead of silently masking the issue.

## Safety Notes

Adjusted valuation is a research basis only. It is not a live trading simulation, not an execution-price model, not investment advice, and not an automatic order system.
