# Data Realism Spec

`v0.4.0-data-quality-realism` adds optional offline CSV structures that model common A-share data realities before any real external data connection is introduced. The project still does not call external APIs, scrape websites, connect to brokers, or place live orders.

## Why Trade Calendar Matters

A-share research cannot assume every natural day is tradable. Weekends, holidays, exchange-specific closures, and special suspension windows affect signal timing, holding periods, turnover, and backtest execution. `trade_calendar.csv` provides a local point of reference for open dates and neighboring open dates without changing the existing daily bar logic.

## Current State Pollution

`stock_master.csv` contains current descriptive fields such as board, industry, ST flags, suspension, and delisting-risk status. Those fields can pollute historical research when today's state is applied to past dates. For example, a stock that became ST later should not be treated as ST before the effective date.

## Stock Status History

`stock_status_history.csv` models effective-dated stock state:

- board and industry history
- ST / *ST flags
- suspension state
- delisting-risk and listing status
- `available_at` for point-in-time visibility

The first version only provides query tools and quality/audit checks. It does not replace universe filters yet.

## Adjustment Factors

`adjustment_factor.csv` stores qfq, hfq, raw, or none factors by stock and trade date. It enables later adjusted daily bar generation while keeping this task scoped to lookup and coverage checks. This task does not modify `daily_bar.csv` prices.

## Corporate Actions

`corporate_action.csv` records dividends, bonus shares, transfers, rights issues, splits, and other actions. These events affect adjusted prices, returns, and backtest realism. `available_at` or `publish_date` controls whether an action was visible at a decision time.

## Optional CSV Fields

`trade_calendar.csv`:

```text
calendar_date,exchange,is_open,previous_open_date,next_open_date,notes
```

`exchange` is one of `sse`, `szse`, `bse`, or `all`.

`stock_status_history.csv`:

```text
ts_code,effective_start,effective_end,board,industry,is_st,is_star_st,is_suspended,is_delisting_risk,listing_status,source_name,available_at,notes
```

`board` is `main`, `chinext`, `star`, `bse`, `unknown`, or empty. `listing_status` is `listed`, `suspended`, `delisting_risk`, `delisted`, or `unknown`.

`adjustment_factor.csv`:

```text
ts_code,trade_date,adj_factor,adj_type,source_name,available_at,notes
```

`adj_type` is `qfq`, `hfq`, `none`, or `raw`.

`corporate_action.csv`:

```text
ts_code,action_date,ex_date,record_date,publish_date,action_type,cash_dividend,bonus_share_ratio,transfer_share_ratio,rights_issue_ratio,source_name,available_at,notes
```

`action_type` is `dividend`, `bonus_share`, `transfer_share`, `rights_issue`, `split`, or `other`.

## Quality Report Enhancements

When optional realism CSV files exist, `quality-report` adds checks for duplicate calendar/status/factor/action keys, invalid date ordering, unknown `ts_code` references, status interval overlaps, board-prefix conflicts, missing `available_at`, factor coverage gaps, and suspicious corporate action dates.

Missing optional files do not fail `validate-data`, `quality-report`, or `run-pipeline`.

## Leakage Audit Enhancements

When optional realism CSV files exist, `audit-leakage` checks whether status history, adjustment factors, and corporate actions were visible at the decision time. Missing visibility timestamps produce warnings. Future `available_at` values produce warnings because those rows must not be used for historical decisions.

## CLI Usage

```bash
python -m ashare_alpha inspect-realism-data
python -m ashare_alpha inspect-realism-data --format json

python -m ashare_alpha check-trading-calendar --start 2026-01-01 --end 2026-03-31
python -m ashare_alpha check-trading-calendar --start 2026-01-01 --end 2026-03-31 --exchange all --format json
```

Both commands read only local CSV files.

## Safety Boundary

This layer is data structure and validation groundwork only. It does not connect to Tushare, AkShare, broker APIs, or any external service. It does not scrape websites. It does not submit orders. It does not guarantee returns.
