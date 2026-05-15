# PIPELINE_SPEC

`run-pipeline` is the daily research orchestration command for `ashare-alpha-lab`. It runs the existing offline research modules in order and writes all outputs into one dated directory. It does not add strategies, change scoring logic, change backtest logic, change the probability model, call external APIs, scrape websites, connect to brokers, or submit orders.

## Command

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20
```

With optional probability prediction:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --model-dir outputs/models/probability_2026-01-05_2026-03-20
```

JSON summary:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --model-dir outputs/models/probability_2026-01-05_2026-03-20 \
  --format json
```

Require probability prediction:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --model-dir missing_model_dir \
  --require-probability
```

Run point-in-time leakage audit after data validation:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --audit-leakage
```

Run data quality report after data validation:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --quality-report
```

## Steps

Required steps:

1. `validate_data`
2. `build_universe`
3. `compute_factors`
4. `compute_events`
5. `generate_signals`
6. `daily_report`

Optional step:

7. `predict_probabilities`

Optional audit step:

- `audit_leakage`, enabled only with `--audit-leakage`, runs after `validate_data`.

Optional quality step:

- `quality_report`, enabled only with `--quality-report`, runs after `validate_data`.

The runner directly calls Python modules such as `LocalCsvAdapter`, `UniverseBuilder`, `FactorBuilder`, `EventFeatureBuilder`, `SignalGenerator`, `DailyReportBuilder`, and `ProbabilityPredictor`. It does not call this project's CLI through subprocess.

## Probability Logic

If `--model-dir` is not provided, probability prediction is marked `SKIPPED` and the overall pipeline can still be `SUCCESS`.

If `--model-dir` is provided and prediction succeeds, `probability_daily_YYYY-MM-DD.csv` is generated.

If probability prediction fails:

- without `--require-probability`: the pipeline status is `PARTIAL`, and required daily research outputs remain available.
- with `--require-probability`: the pipeline status is `FAILED`, and the process returns nonzero.

## Leakage Audit Logic

By default, the pipeline does not run point-in-time leakage audit, so existing behavior is unchanged.

When `--audit-leakage` is provided:

- the audit runs after `validate_data`.
- `audit/audit_report.json`, `audit/audit_report.md`, and `audit/data_snapshot.json` are written under the pipeline output directory.
- warning/info findings are recorded in the manifest and the pipeline continues.
- error-level findings mark `audit_leakage` as `FAILED` and the overall pipeline as `FAILED`.

## Data Quality Logic

By default, the pipeline does not run data quality reporting, so existing behavior is unchanged.

When `--quality-report` is provided:

- the report runs after `validate_data`.
- `quality/quality_report.json`, `quality/quality_report.md`, and `quality/quality_issues.csv` are written under the pipeline output directory.
- warning/info findings are recorded in the manifest and the pipeline continues.
- error-level findings mark `quality_report` as `FAILED` and the overall pipeline as `FAILED`.

## Output Directory

Default output directory:

```text
outputs/pipelines/pipeline_YYYY-MM-DD/
```

Example:

```text
outputs/pipelines/pipeline_2026-03-20/
  manifest.json
  pipeline_summary.md
  universe_daily_2026-03-20.csv
  factor_daily_2026-03-20.csv
  event_daily_2026-03-20.csv
  signal_daily_2026-03-20.csv
  probability_daily_2026-03-20.csv
  audit/
    audit_report.json
    audit_report.md
    data_snapshot.json
  quality/
    quality_report.json
    quality_report.md
    quality_issues.csv
  daily_report/
    daily_report.md
    daily_report.json
    buy_candidates.csv
    watch_candidates.csv
    blocked_stocks.csv
    high_risk_stocks.csv
    event_risk_stocks.csv
```

`probability_daily_YYYY-MM-DD.csv` is present only when a model directory is provided and prediction succeeds.

The `audit/` directory is present only when `--audit-leakage` is provided.

The `quality/` directory is present only when `--quality-report` is provided.

## manifest.json

`manifest.json` is the machine-readable pipeline record. It includes:

- pipeline date, generated time, data/config/output/model directories.
- overall status.
- step-level status, timestamps, duration, output paths, summaries, and error messages.
- research summary counts: total stocks, allowed universe, BUY / WATCH / BLOCK, high-risk count, market regime.
- probability predictable count when available.
- leakage audit path when available.
- quality report path when available.
- core output paths.
- research risk disclaimer.

## pipeline_summary.md

`pipeline_summary.md` is the human-readable overview. It includes:

1. Basic information.
2. Overall status.
3. Step status table.
4. Research summary.
5. Main output files.
6. Risk notice.

It is a quick index and does not replace `daily_report/daily_report.md`.

## Status Meaning

- `SUCCESS`: all required steps succeeded. Probability may be skipped when no model directory is provided.
- `PARTIAL`: required steps succeeded, but optional probability prediction failed without `--require-probability`.
- `FAILED`: a required step failed, audit found error-level issues, or probability prediction failed while `--require-probability` was set.

## Risk Boundary

The pipeline is for research and backtesting only. It is not investment advice, does not promise returns, will not automatically place orders, and does not connect to broker APIs.
