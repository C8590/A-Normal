# REPORT_SPEC

`ashare-alpha-lab` reports are Chinese-readable research artifacts built from existing local CSV data, configured rules, generated factors, generated events, generated signals, and offline backtest results. They do not add strategies, machine learning, external APIs, scraping, broker integration, or live order submission.

## daily-report

```bash
python -m ashare_alpha daily-report --date 2026-03-20
python -m ashare_alpha daily-report --date 2026-03-20 --format json
python -m ashare_alpha daily-report --date 2026-03-20 --output-dir outputs/reports/test_daily
```

Arguments:

- `--date YYYY-MM-DD`: required report date.
- `--data-dir PATH`: defaults to `data/sample/ashare_alpha`.
- `--config-dir PATH`: defaults to `configs/ashare_alpha`.
- `--output-dir PATH`: defaults to `outputs/reports/daily_YYYY-MM-DD`.
- `--format text/json`: controls CLI summary output; report files are always saved.

The command validates local CSV inputs, builds `universe_daily`, `factor_daily`, `event_daily`, and `signal_daily` in memory, then builds the report from those records without changing signal-generation logic.

## backtest-report

```bash
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20 --reuse-backtest-dir outputs/backtests/backtest_2026-01-05_2026-03-20
```

Arguments:

- `--start YYYY-MM-DD`: required start date.
- `--end YYYY-MM-DD`: required end date; must be later than `--start`.
- `--data-dir PATH`: defaults to `data/sample/ashare_alpha`.
- `--config-dir PATH`: defaults to `configs/ashare_alpha`.
- `--output-dir PATH`: defaults to `outputs/reports/backtest_START_END`.
- `--format text/json`: controls CLI summary output; report files are always saved.
- `--reuse-backtest-dir PATH`: reads `metrics.json`, `trades.csv`, and `daily_equity.csv` from an existing backtest output directory instead of running the engine again.

## Output Files

Daily report directory:

- `daily_report.md`
- `daily_report.json`
- `buy_candidates.csv`
- `watch_candidates.csv`
- `blocked_stocks.csv`
- `high_risk_stocks.csv`
- `event_risk_stocks.csv`

Backtest report directory:

- `backtest_report.md`
- `backtest_report.json`
- `symbol_summary.csv`
- `reject_reasons.csv`

CSV list fields are joined with the Chinese semicolon `；`.

## Daily Report Structure

The Markdown daily report contains:

1. 摘要: date, market regime, stock counts, BUY / WATCH / BLOCK counts, high-risk count.
2. BUY 候选: sorted by `stock_score` descending; if empty, it explicitly states `当前无 BUY 信号`.
3. WATCH 观察名单: top 20 by `stock_score`.
4. BLOCK 禁买 / 剔除股票: blocked signals and universe exclusions with readable reasons.
5. 事件风险: stocks with nonzero event risk score or event block-buy flags.
6. 股票池剔除原因统计: universe exclusion reason counts.
7. 当前配置摘要: initial cash, max positions, lot size, commission, stamp tax, slippage.
8. 风险提示: research-only boundary and no automatic order placement.

## Backtest Report Structure

The Markdown backtest report contains:

1. 回测区间.
2. 核心指标: initial cash, final equity, total return, annualized return, drawdown, Sharpe, win rate, turnover.
3. 交易摘要: trade counts, filled/rejected counts, no-trade explanation.
4. 拒绝成交原因: counted by reject reason.
5. 标的交易归因: filled trades, buy/sell counts, realized PnL, rejected trades by symbol.
6. 最近净值曲线: last five daily equity rows.
7. 配置摘要: rebalance frequency, execution price, T+1, lot size, costs, slippage.
8. 风险提示: simulated research boundary.

## Risk Boundary

Reports are for research review and engineering validation only. They are not investment advice, do not promise future performance, and do not represent live trading results. The current system will not connect to brokers and will not automatically submit orders.
