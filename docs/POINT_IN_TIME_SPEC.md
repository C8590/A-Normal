# POINT_IN_TIME_SPEC

Point-in-time means a research decision for `trade_date` may only use records that were already visible at that decision time. This prevents future-function leakage, where later information silently improves historical signals or backtests.

This project still uses local CSV sample data only. The audit tools do not call external APIs, scrape websites, connect to brokers, or place orders.

## Available Time Rules

- `daily_bar`: a daily bar for `trade_date` is available at `trade_date 15:30`. The current daily research flow assumes after-close decisions.
- `financial_summary`: available at `publish_date 00:00`. `report_date` is the accounting period and must not be used as the visibility date.
- `announcement_event`: available at `event_time`.

`available_at <= decision_time` means a record is available. The helper `make_decision_time(trade_date, "after_close")` returns `15:30`; `"before_open"` returns `09:00`.

## DataSnapshot

`DataSnapshot` records the audit context:

- `snapshot_id`
- creation time
- source name
- data version or import batch
- data/config directories
- row counts
- minimum and maximum business dates for each local CSV table

It does not modify the source data. It is intended to make later research runs easier to reproduce and inspect.

## LeakageAuditReport

`LeakageAuditReport` is the audit result. It contains:

- audit date or date range
- data/config directories
- source name and data version
- error, warning, and info counts
- individual `LeakageIssue` entries
- `passed`, which is true only when there are no error-level issues

The audit checks common risks:

- financial `publish_date < report_date`, treated as error.
- financial records whose report period ended by `trade_date` but whose `publish_date` is still in the future, recorded as warning.
- announcement events after the research date, recorded as info.
- daily-bar after-close availability rule, recorded as info.
- `stock_master` current-state fields such as board, industry, ST, suspension, and delisting risk, recorded as warning because real data should eventually use historical effective dates.
- missing `source_name` or `data_version`.

## CLI

Audit one date:

```bash
python -m ashare_alpha audit-leakage --date 2026-03-20
python -m ashare_alpha audit-leakage --date 2026-03-20 --format json
```

Audit a range:

```bash
python -m ashare_alpha audit-leakage --start 2026-01-05 --end 2026-03-20
```

Default outputs:

```text
outputs/audit/leakage_YYYY-MM-DD/
  audit_report.json
  audit_report.md
  data_snapshot.json
```

or:

```text
outputs/audit/leakage_START_END/
  audit_report.json
  audit_report.md
  data_snapshot.json
```

The command returns nonzero when error-level issues are found. Warning and info findings still produce files and return zero.

## Pipeline Integration

Leakage audit is disabled by default:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20
```

Enable it explicitly:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20 --audit-leakage
```

When enabled, the audit runs after `validate_data`. Error-level findings fail the pipeline. Warning/info findings are recorded in `manifest.json` and the pipeline continues.

## Limits

The audit is a research aid. It checks visibility rules and common future-function risks, but it cannot prove the dataset is completely correct. The system remains a research and backtesting system only; it is not investment advice, does not automatically place orders, and does not connect to broker APIs.
