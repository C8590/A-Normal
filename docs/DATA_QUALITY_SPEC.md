# DATA_QUALITY_SPEC

Data quality reporting scans the four standard local CSV files and reports suspicious records, coverage gaps, and cross-table inconsistencies. It complements `validate-data`: validation answers whether records can be loaded into the internal models; quality reporting also highlights values that may be valid syntactically but risky for research.

The command uses only local CSV files. It does not call external APIs, scrape websites, connect to brokers, or place orders.

## Command

Default sample data:

```bash
python -m ashare_alpha quality-report
python -m ashare_alpha quality-report --format json
```

Imported data:

```bash
python -m ashare_alpha quality-report \
  --data-dir data/imports/local_csv/sample_v1 \
  --source-name local_csv \
  --data-version sample_v1 \
  --date 2026-03-20
```

Default output directory:

```text
outputs/quality/quality_YYYYMMDD_HHMMSS/
  quality_report.json
  quality_report.md
  quality_issues.csv
```

The command returns nonzero when error-level issues are found. Warning and info findings still produce files and return zero.

## Report Fields

`quality_report.json` contains:

- `generated_at`
- `data_dir`
- `source_name`
- `data_version`
- issue counts
- row counts
- coverage summary
- full issue list
- `passed`
- Chinese summary text

`quality_issues.csv` contains one row per issue:

- `severity`
- `dataset_name`
- `issue_type`
- `ts_code`
- `trade_date`
- `field_name`
- `message`
- `recommendation`

## Checks

`stock_master.csv`:

- duplicate `ts_code`
- missing `symbol`, `name`, or `list_date`
- invalid `exchange` or `board`
- `delist_date` before `list_date`
- possible board/code-prefix mismatch

`daily_bar.csv`:

- unknown `ts_code`
- duplicate `ts_code + trade_date`
- negative prices
- invalid high/low/open/close shape
- suspicious trading status versus amount or volume
- extreme one-day return
- too few records per stock
- large date gaps
- invalid or suspicious price-limit fields

`financial_summary.csv`:

- unknown `ts_code`
- `publish_date` before `report_date`
- duplicate `ts_code + report_date`
- extreme financial ratios
- all financial numeric fields missing

`announcement_event.csv`:

- unknown `ts_code`
- missing title
- missing source
- invalid strength, direction, or risk level
- event time far after the daily-bar date range
- duplicate event identity

Cross-table coverage:

- stock without any daily bars
- stock without financial summary
- stock without announcement events
- daily-bar date range too short
- daily-bar maximum date before target research date
- financial publish dates all after the daily-bar maximum date

## Pipeline Integration

Quality reporting is disabled by default:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20
```

Enable it explicitly:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20 --quality-report
```

When enabled, the report runs after `validate_data`. Error-level findings fail the pipeline. Warning/info findings are recorded in `manifest.json` and the pipeline continues.

## Import Integration

Quality reporting is disabled by default for imports:

```bash
python -m ashare_alpha import-data \
  --source-name local_csv \
  --source-data-dir data/sample/ashare_alpha \
  --data-version sample_v1
```

Enable it explicitly:

```bash
python -m ashare_alpha import-data \
  --source-name local_csv \
  --source-data-dir data/sample/ashare_alpha \
  --data-version sample_v1 \
  --overwrite \
  --quality-report
```

When enabled after a successful import, the quality files are written into the imported version directory. If quality errors are found, validation status is not rewritten, but `import_manifest.json` notes that the quality report needs review.

## Limits

The quality report is an auxiliary check. It cannot prove that data is fully correct, and it does not repair data. The system remains an offline research system, does not automatically place orders, and is not investment advice.
