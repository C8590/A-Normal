# Adjusted Research Report Spec

## 1. Why This Exists

`adjusted-research-report` combines the adjusted-price work from v0.5, v0.6, and v0.7 into one offline research comparison layer.

It compares raw, qfq, and hfq price bases for factor outputs, backtest valuation outputs, summary differences, research warnings, dashboard artifacts, and optional experiment records.

## 2. raw / qfq / hfq

- `raw` is the original local CSV daily bar price basis.
- `qfq` is a forward-adjusted research valuation basis.
- `hfq` is a backward-adjusted research valuation basis.

Adjusted prices are research valuation inputs only. They are not real execution prices.

## 3. Factor Differences

The report computes factors for `raw`, `qfq`, and `hfq` on the requested target date, then compares `raw` vs `qfq` and `raw` vs `hfq`.

The summary includes compared row count, changed moving-average state counts, maximum absolute momentum and volatility differences, and the top rows by absolute difference.

## 4. Backtest Differences

The report runs backtests for `raw`, `qfq`, and `hfq` over the requested date range, then compares `raw` vs `qfq` and `raw` vs `hfq`.

The summary includes total return, annualized return, max drawdown, sharpe, final equity, and trade count differences. Execution constraints remain based on raw daily bars.

## 5. Command Usage

```bash
python -m ashare_alpha adjusted-research-report --date 2026-03-20 --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha adjusted-research-report --date 2026-03-20 --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha adjusted-research-report --date 2026-03-20 --start 2026-01-05 --end 2026-03-20 --record-experiment
```

## 6. Output Files

Default output root:

```text
outputs/adjusted_research/adjusted_research_YYYYMMDD_HHMMSS/
```

Key files and directories:

- `adjusted_research_report.json`
- `adjusted_research_report.md`
- `adjusted_research_summary.csv`
- `factor_compare_raw_qfq/`
- `factor_compare_raw_hfq/`
- `backtest_raw/`
- `backtest_qfq/`
- `backtest_hfq/`
- `backtest_compare_raw_qfq/`
- `backtest_compare_raw_hfq/`

## 7. Dashboard Integration

`build-dashboard` scans:

```text
outputs/adjusted_research/**/adjusted_research_report.json
```

It records the artifact type as `adjusted_research` and summarizes status, factor comparison count, backtest comparison count, warning count, and output path.

## 8. Experiment Integration

`adjusted-research-report --record-experiment` records command metadata and extracts:

- `factor_comparison_count`
- `backtest_comparison_count`
- `warning_count`
- `raw_qfq_total_return_diff`
- `raw_qfq_sharpe_diff`
- `raw_hfq_total_return_diff`
- `raw_hfq_sharpe_diff`

Experiment recording is optional and does not change the default command behavior.

## 9. Boundaries

- qfq/hfq are research valuation bases.
- Real execution constraints remain based on raw daily bars.
- adjusted price does not represent real execution price.
- This report is not investment advice.
- It does not guarantee future returns.
- It does not automatically place orders.
- It does not connect to brokers.
- It does not call external APIs.
