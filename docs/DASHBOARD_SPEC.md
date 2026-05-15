# Dashboard Spec

The Research Dashboard is a read-only index over existing research outputs. It scans completed artifacts, summarizes their status and key metrics, and renders a static Markdown dashboard plus JSON and CSV tables.

It does not change strategy logic, backtest logic, probability-model logic, or configuration files.

## 1. Why A Dashboard Exists

The project can produce many output directories from pipelines, backtests, sweeps, walk-forward validation, experiments, candidate selection, data quality checks, leakage audits, security scans, and probability training. The dashboard gives a single research overview so a user can see what has been run, what needs review, and which research candidates may deserve another validation round.

The dashboard is not investment advice and does not guarantee future returns.

## 2. build-dashboard

```bash
python -m ashare_alpha build-dashboard
python -m ashare_alpha build-dashboard --format json
python -m ashare_alpha build-dashboard --outputs-root outputs --output-dir outputs/dashboard/manual_run
```

The command scans `outputs/` by default and writes:

- `dashboard_index.json`
- `dashboard_summary.json`
- `dashboard.md`
- `dashboard_tables/artifacts.csv`
- `dashboard_tables/recent_experiments.csv`
- `dashboard_tables/top_candidates.csv`
- `dashboard_tables/warning_items.csv`

If `outputs_root` does not exist, the command fails. If no artifacts are found, it still writes a dashboard that says no research artifacts were found.

## 3. show-dashboard

```bash
python -m ashare_alpha show-dashboard --path outputs/dashboard/dashboard_ID
python -m ashare_alpha show-dashboard --path outputs/dashboard/dashboard_ID/dashboard_index.json
python -m ashare_alpha show-dashboard --path outputs/dashboard/dashboard_ID/dashboard_summary.json --format json
```

The command prints artifact counts, latest artifact references, warning items, and the Chinese summary text.

## 4. dashboard_index.json

`dashboard_index.json` contains:

- `generated_at`
- `outputs_root`
- `artifact_count`
- `artifacts_by_type`
- `artifacts`

Each artifact includes:

- `artifact_id`
- `artifact_type`
- `name`
- `path`
- `created_at`
- `status`
- `summary`
- `related_paths`

Supported artifact types are pipeline, backtest, sweep, walkforward, experiment, candidate_selection, quality_report, leakage_audit, security_scan, probability_model, and unknown.

## 5. dashboard.md

The Markdown report contains:

1. Overview
2. Latest research artifacts
3. Latest Pipeline
4. Latest Backtest
5. Latest Sweep
6. Latest Walk-forward
7. Candidate configurations
8. Recent experiments
9. Risk and warnings
10. Safety notes

## 6. CSV Tables

`dashboard_tables/artifacts.csv` lists all scanned artifacts. Other tables provide flattened views of recent experiments, top candidate scores, and warning items. List and dict fields are encoded as JSON strings to preserve structure.

## 7. warning_items

Warning items are collected from:

- quality reports with `error_count > 0`,
- leakage audit reports with `error_count > 0`,
- security scan reports with `error_count > 0`,
- walk-forward results with `overfit_warnings`,
- sweeps with `failed_count > 0`,
- pipelines with status other than `SUCCESS`,
- files that look like research artifacts but cannot be read.

## 8. Safety Boundary

The dashboard only summarizes research artifacts. It does not fetch data, scrape websites, call external APIs, connect to brokers, submit orders, choose a live configuration, constitute investment advice, or guarantee future returns.
