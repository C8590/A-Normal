# ashare-alpha-lab

`ashare-alpha-lab` is an A-share individual-stock research lab. The MVP is limited to research, backtesting, signal generation, and reporting. It does not do live trading, broker integration, high-frequency trading, web scraping, or external API calls.

Current MVP release: `0.1.0-mvp`. The runtime version is stored in `VERSION` and `ashare_alpha.__version__`; `pyproject.toml` keeps the PEP 440 compatible package version `0.1.0` for installation compatibility.

## Goals

- Build a small, testable Python project for A-share stock research.
- Use local CSV sample data first.
- Keep trading rules, fees, scoring thresholds, and backtest constraints in YAML config.
- Require human-readable Chinese reasons for future filters and signals.
- Avoid secrets, API keys, broker interfaces, and order submission code.

## Project Layout

```text
configs/ashare_alpha/       # YAML config used by the new project
data/sample/ashare_alpha/   # local CSV sample data
docs/                       # project specs
src/ashare_alpha/           # new project source code
tests/                      # pytest tests
```

The older `src/a_normal` package still exists in this workspace for historical tests. New `ashare_alpha` code must not import it.

## Development Environment

Recommended Windows interpreter:

```powershell
py -3.12 --version
```

Install the project in editable mode:

```powershell
py -3.12 -m pip install -e .
py -3.12 -m pip install -e ".[dev]"
```

Verify the package entrypoint:

```powershell
py -3.12 -m ashare_alpha --help
ashare-alpha --help
py -3.12 -m ashare_alpha show-version
py -3.12 -m ashare_alpha show-version --format json
```

Run environment diagnostics and smoke tests:

```powershell
py -3.12 scripts/dev_check.py
py -3.12 scripts/dev_check.py --format json
py -3.12 scripts/smoke_test.py
py -3.12 scripts/smoke_test.py --full
py -3.12 -m ashare_alpha release-check
py -3.12 -m ashare_alpha release-check --format json
```

PowerShell helpers:

```powershell
.\scripts\install_dev.ps1
.\scripts\smoke_test.ps1
.\scripts\smoke_test.ps1 -Full
```

If editable install has not been run yet, this temporary fallback can be used from the repository root:

```powershell
$env:PYTHONPATH = "src"
```

That fallback is only for local diagnosis. Editable install is the recommended workflow. See `docs/DEVELOPMENT_SETUP.md` and `docs/COMMAND_MATRIX.md`.

## Release Checks

`release-check` freezes the MVP release boundary into local artifacts under `outputs/release/v0.1.0-mvp/`:

- `release_manifest.json`
- `release_checklist.md`

```bash
python -m ashare_alpha release-check
python -m ashare_alpha release-check --output-dir outputs/release/v0.1.0-mvp
```

The check verifies version files, release docs, command matrix files, security flags, forbidden imports, suspicious live-order names, test/tool availability, and current release notes. It does not run heavy backtests, does not call external APIs, and does not connect to brokers. See `CHANGELOG.md`, `RELEASE_NOTES.md`, and `docs/RELEASE_PROCESS.md`.

## Configuration

The new project reads only `configs/ashare_alpha/` by default:

- `universe.yaml`
- `trading_rules.yaml`
- `fees.yaml`
- `factors.yaml`
- `scoring.yaml`
- `backtest.yaml`

`factors.yaml` also contains the rule-based `event_scoring` section used by the announcement event engine. Event windows, half-life decay, scores, risk scores, source weights, and block-buy event types all come from config.

Show the validated config:

```bash
python -m ashare_alpha show-config
python -m ashare_alpha show-config --config-dir tests/fixtures/configs/valid
```

## Local CSV Data

The default sample data lives in `data/sample/ashare_alpha/`:

- `stock_master.csv`
- `daily_bar.csv`
- `financial_summary.csv`
- `announcement_event.csv`

Validate local CSV data:

```bash
python -m ashare_alpha validate-data
python -m ashare_alpha validate-data --data-dir data/sample/ashare_alpha
python -m ashare_alpha validate-data --format json
```

The data layer currently supports local CSV only. Future data adapters can be added behind the `DataAdapter` interface without changing downstream modules.

### Optional Data Realism CSVs

The `v0.4.0-data-quality-realism` stage adds optional local CSV files for A-share data realism:

- `trade_calendar.csv`
- `stock_status_history.csv`
- `adjustment_factor.csv`
- `corporate_action.csv`

These files model trading calendars, historical ST / suspension / board / industry / listing states, adjustment factors, and corporate actions. They are optional: the four required CSVs above remain the only mandatory inputs for `validate-data` and `run-pipeline`.

Inspect the optional realism layer:

```bash
python -m ashare_alpha inspect-realism-data
python -m ashare_alpha inspect-realism-data --format json
python -m ashare_alpha check-trading-calendar --start 2026-01-01 --end 2026-03-31
python -m ashare_alpha check-trading-calendar --start 2026-01-01 --end 2026-03-31 --format json
```

When present, the optional files enhance `quality-report` and `audit-leakage`; they do not change strategy, backtest, signal, or probability model logic. See `docs/DATA_REALISM_SPEC.md`.

### Adjusted Daily Bars

`build-adjusted-bars` generates auditable `raw`, `qfq`, or `hfq` daily bars under `outputs/adjusted/` by combining local `daily_bar.csv` with optional `adjustment_factor.csv`. It is an offline research artifact generator only: it does not change factor, backtest, probability, or pipeline defaults.

```bash
python -m ashare_alpha build-adjusted-bars --date 2026-03-20 --adj-type qfq
python -m ashare_alpha build-adjusted-bars --start 2026-01-05 --end 2026-03-20 --adj-type qfq
python -m ashare_alpha build-adjusted-bars --start 2026-01-05 --end 2026-03-20 --adj-type raw
```

The report states that adjusted prices are generated from input factors for research use, are not official exchange-adjusted prices, are not investment advice, and never submit orders. See `docs/ADJUSTED_PRICE_SPEC.md`.

Inspect registered data source metadata:

```bash
python -m ashare_alpha list-data-sources
python -m ashare_alpha list-data-sources --format json
python -m ashare_alpha inspect-data-source --name local_csv
python -m ashare_alpha inspect-data-source --name tushare_stub
```

`local_csv` is the only available data source. `tushare_stub` and `akshare_stub` are placeholders for future adapter work; they do not import vendor SDKs, do not call external APIs, and do not fetch real data. See `docs/DATA_SOURCE_SPEC.md`.

## Offline Adapter Contracts

Future real data-source adapters are tested offline first with local synthetic fixtures. Contract validation checks external CSV field coverage, and fixture conversion maps Tushare-like or AkShare-like CSVs into the standard four local tables.

```bash
python -m ashare_alpha validate-adapter-contract --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like
python -m ashare_alpha validate-adapter-contract --source-name akshare_like --fixture-dir tests/fixtures/external_sources/akshare_like --format json

python -m ashare_alpha convert-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --output-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha convert-source-fixture --source-name akshare_like --fixture-dir tests/fixtures/external_sources/akshare_like --output-dir data/imports/akshare_like/contract_sample
```

Converted fixture output can be used by the existing local-data commands:

```bash
python -m ashare_alpha validate-data --data-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha quality-report --data-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha import-data --source-name tushare_like --source-data-dir data/imports/tushare_like/contract_sample --data-version contract_sample --overwrite
```

This layer is still fully offline: it does not import Tushare or AkShare SDKs, call external APIs, scrape websites, connect to brokers, or place orders. See `docs/ADAPTER_CONTRACT_SPEC.md`.

## External Cache Store

The external cache store is the staging layer for future real data adapters. In the current branch it is still offline only: it copies local fixture CSV files into `data/cache/external/{source_name}/{cache_version}/raw/`, writes `cache_manifest.json`, and can materialize the raw cache into the standard four-table `normalized/` directory.

```bash
python -m ashare_alpha cache-source-fixture \
  --source-name tushare_like \
  --fixture-dir tests/fixtures/external_sources/tushare_like \
  --cache-version contract_sample

python -m ashare_alpha list-caches
python -m ashare_alpha inspect-cache --source-name tushare_like --cache-version contract_sample

python -m ashare_alpha materialize-cache \
  --source-name tushare_like \
  --cache-version contract_sample
```

Normalized cache output can feed the existing local workflow:

```bash
python -m ashare_alpha validate-data --data-dir data/cache/external/tushare_like/contract_sample/normalized
python -m ashare_alpha import-data --source-name tushare_like --source-data-dir data/cache/external/tushare_like/contract_sample/normalized --data-version contract_sample --quality-report
python -m ashare_alpha run-pipeline --date 2026-03-20 --data-dir data/imports/tushare_like/contract_sample --audit-leakage --quality-report --check-security
```

Cache commands load the project security config and require network, broker connections, and live trading to remain disabled. They do not read real API keys and do not fetch data. See `docs/CACHE_STORE_SPEC.md`.

## Source Runtime Profiles

External-source runtime profiles live under `configs/ashare_alpha/source_profiles/`. They describe how an external source can run in the current offline framework:

- `offline_replay` reads local fixture CSVs and converts them into the standard four-table layout.
- `cache_only` copies an existing local standard four-table cache and validates it.
- `live_disabled` is a future placeholder and cannot run.

Inspect and materialize profiles:

```bash
python -m ashare_alpha list-source-profiles
python -m ashare_alpha list-source-profiles --format json
python -m ashare_alpha inspect-source-profile --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml

python -m ashare_alpha materialize-source \
  --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml \
  --data-version contract_sample \
  --quality-report
```

Materialized output is written to `data/materialized/{source_name}/{data_version}/` and can feed the existing local-data workflow:

```bash
python -m ashare_alpha validate-data --data-dir data/materialized/tushare_like_offline/contract_sample
python -m ashare_alpha import-data --source-name tushare_like_offline --source-data-dir data/materialized/tushare_like_offline/contract_sample --data-version contract_sample --overwrite --quality-report
python -m ashare_alpha run-pipeline --date 2026-03-20 --data-dir data/imports/tushare_like_offline/contract_sample --audit-leakage --quality-report --check-security
```

The runtime profile layer is also fully offline in this MVP: it does not import vendor SDKs, call external APIs, scrape websites, read real API keys, connect to brokers, or submit orders. Future real API adapters must pass through `NetworkGuard` before any network access. See `docs/SOURCE_RUNTIME_SPEC.md`.

## Real Data Offline Drill

`run-realdata-offline-drill` is the v0.3 rehearsal workflow for future real-data ingestion. It still uses only local offline fixtures and existing cache/materialize/import/pipeline builders; it does not fetch data, import vendor SDKs, scrape websites, connect to brokers, or place orders.

```bash
python -m ashare_alpha run-realdata-offline-drill --spec configs/ashare_alpha/realdata/tushare_like_offline_drill.yaml
python -m ashare_alpha run-realdata-offline-drill --spec configs/ashare_alpha/realdata/akshare_like_offline_drill.yaml --format json
python -m ashare_alpha show-realdata-drill --path outputs/realdata/<drill_id>/drill_result.json
```

Each drill writes `drill_result.json`, `drill_report.md`, and `step_summary.csv` under `outputs/realdata/{drill_id}/`, plus cache, materialized data, validation, optional quality/audit/security outputs, pipeline output, frontend, dashboard, and an experiment record. The report states the offline safety boundary clearly: research only, no automatic orders, no investment advice, and no guaranteed returns. See `docs/REAL_DATA_OFFLINE_DRILL_SPEC.md`.

## Security Layer

Security defaults live in `configs/ashare_alpha/security.yaml`: offline mode is on, network access is off, broker connections are off, and live trading is off. Secrets must be referenced by environment variable name only, never written as raw API keys or tokens.

```bash
python -m ashare_alpha check-security
python -m ashare_alpha check-security --format json
python -m ashare_alpha check-secrets
python -m ashare_alpha check-secrets --format json
python -m ashare_alpha show-network-policy
python -m ashare_alpha show-network-policy --format json
```

`list-data-sources` and `inspect-data-source` include a security summary. Pipelines can opt into a preflight security scan without changing default behavior:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20 --check-security
```

Future real data-source adapters must use `NetworkGuard` before any network access. The current system still does not call external APIs, read `.env` files, scrape websites, connect to brokers, or submit orders. See `docs/SECURITY_SPEC.md`.

## Versioned Data Imports

Use `import-data` to copy a local CSV batch into a versioned directory under `data/imports/{source_name}/{data_version}/`. The command copies the four standard CSV files, validates them with `LocalCsvAdapter`, and writes an import manifest, validation report, and point-in-time data snapshot.

```bash
python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha
python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha --data-version sample_v1
python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha --data-version sample_v1 --overwrite --format json
python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha --data-version sample_v1 --overwrite --quality-report
```

Inspect imported batches:

```bash
python -m ashare_alpha list-imports
python -m ashare_alpha list-imports --format json
python -m ashare_alpha inspect-import --source-name local_csv --data-version sample_v1
```

Imported data can be passed to existing commands without changing their defaults:

```bash
python -m ashare_alpha validate-data --data-dir data/imports/local_csv/sample_v1
python -m ashare_alpha run-pipeline --date 2026-03-20 --data-dir data/imports/local_csv/sample_v1 --audit-leakage
```

This layer only copies local CSV files. `--quality-report` is optional and disabled by default; when enabled it writes `quality_report.json`, `quality_report.md`, and `quality_issues.csv` into the imported data directory. The import layer does not connect to external APIs or brokers and does not place orders. See `docs/IMPORT_SPEC.md`.

## Data Quality Report

`quality-report` scans the four standard local CSV files for structural and cross-table quality issues. It is broader than `validate-data`: validation checks whether records can be loaded, while quality reporting also flags suspicious values, short coverage, date gaps, prefix/board mismatches, and missing cross-table coverage.

```bash
python -m ashare_alpha quality-report
python -m ashare_alpha quality-report --format json
python -m ashare_alpha quality-report --data-dir data/imports/local_csv/sample_v1 --source-name local_csv --data-version sample_v1 --date 2026-03-20
```

Outputs are written under `outputs/quality/quality_YYYYMMDD_HHMMSS/`: `quality_report.json`, `quality_report.md`, and `quality_issues.csv`. The report is an auxiliary check and does not repair data. See `docs/DATA_QUALITY_SPEC.md`.

## Daily Universe

`universe_daily` is the daily research universe table. It records every stock from `stock_master`, whether it is allowed, standardized exclusion reasons, Chinese reason text, listing days, latest close, one-lot value, recent average amount, and basic liquidity and risk scores.

Build the sample universe:

```bash
python -m ashare_alpha build-universe --date 2026-03-20
python -m ashare_alpha build-universe --date 2026-03-20 --format json
python -m ashare_alpha build-universe --date 2026-03-20 --output outputs/universe/test.csv
```

The current filters are board exclusion, ST and *ST exclusion, delisting-risk exclusion, suspension and non-trading-day exclusion, minimum listing days, daily-bar sufficiency, recent average amount, one-lot capital affordability, and recent negative events. This is only a research universe and is not investment advice.

## Daily Factors

`factor_daily` contains explainable market, liquidity, volatility, drawdown, moving-average, and limit-price statistics computed only from `trade_date` and earlier local CSV bars.

Compute sample factors:

```bash
python -m ashare_alpha compute-factors --date 2026-03-20
python -m ashare_alpha compute-factors --date 2026-03-20 --format json
python -m ashare_alpha compute-factors --date 2026-03-20 --output outputs/factors/test.csv
```

The factor step does not read `universe_daily`, does not score stocks, and does not create buy or sell signals.

## Announcement Events

`event_daily` contains stock-level announcement event factors built from local `announcement_event.csv`. It scores valid events on or before the requested `trade_date`, applies configured decay and source weights, aggregates each stock's event score and risk score, and marks research-only block-buy flags for severe event risk.

Compute sample event factors:

```bash
python -m ashare_alpha compute-events --date 2026-03-20
python -m ashare_alpha compute-events --date 2026-03-20 --format json
python -m ashare_alpha compute-events --date 2026-03-20 --output outputs/events/test.csv
```

The event engine is a transparent rule model. It does not score stocks, generate buy/sell signals, run probability models, backtest, call external APIs, scrape websites, connect to brokers, or submit orders. See `docs/EVENT_SPEC.md` for formulas and aggregation rules.

## Research Signals

`signal_daily` combines `universe_daily`, `factor_daily`, `event_daily`, and published financial summaries into a transparent research score and BUY / WATCH / BLOCK label. BUY is only a research label with an estimated position size; it is not an order and the system still does not connect to brokers or submit trades.

Generate sample signals:

```bash
python -m ashare_alpha generate-signals --date 2026-03-20
python -m ashare_alpha generate-signals --date 2026-03-20 --format json
python -m ashare_alpha generate-signals --date 2026-03-20 --output outputs/signals/test.csv
```

The signal step does not generate SELL signals because the MVP has no holdings input. See `docs/SIGNAL_SPEC.md` for the scoring formula, risk penalty logic, and signal meanings.

## Backtesting

The backtest engine uses generated research signals for historical simulated execution. Signals are produced after the decision date close and simulated on the next trading day's open, with configured A-share costs and constraints.

Run the sample backtest:

```bash
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --output-dir outputs/backtests/test
```

Outputs are written under `outputs/backtests/backtest_START_END/`: `trades.csv`, `daily_equity.csv`, `metrics.json`, and `summary.md`. The backtest is offline simulation only; it does not submit real orders.

## Research Reports

Daily reports explain the current market state, universe filtering, factor overview, announcement-event risk, BUY / WATCH / BLOCK signals, blocked-buy reasons, config summary, and risk notice:

```bash
python -m ashare_alpha daily-report --date 2026-03-20
python -m ashare_alpha daily-report --date 2026-03-20 --format json
python -m ashare_alpha daily-report --date 2026-03-20 --output-dir outputs/reports/test_daily
```

Daily report files are written under `outputs/reports/daily_YYYY-MM-DD/`: `daily_report.md`, `daily_report.json`, `buy_candidates.csv`, `watch_candidates.csv`, `blocked_stocks.csv`, `high_risk_stocks.csv`, and `event_risk_stocks.csv`.

Backtest research reports explain simulated performance, rejected trade reasons, symbol-level attribution, recent equity curve, config summary, and risk notice:

```bash
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha backtest-report --start 2026-01-05 --end 2026-03-20 --reuse-backtest-dir outputs/backtests/backtest_2026-01-05_2026-03-20
```

Backtest report files are written under `outputs/reports/backtest_START_END/`: `backtest_report.md`, `backtest_report.json`, `symbol_summary.csv`, and `reject_reasons.csv`. Reports are research artifacts only; they do not introduce new strategies, machine learning, broker integration, external APIs, web scraping, or real order submission. See `docs/REPORT_SPEC.md`.

## Baseline Probability Model

The baseline probability model uses historical research signals and future-return labels to estimate research-only win probability and expected return over 5, 10, and 20 trading-day horizons. It is a pure Python score-bin calibration model and does not add machine learning dependencies.

Train the sample model:

```bash
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20 --output-dir outputs/models/test_probability
```

Training outputs are written under `outputs/models/probability_START_END/`: `probability_dataset.csv`, `model.json`, `metrics.json`, `test_predictions.csv`, and `summary.md`.

Predict probabilities for a date:

```bash
python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20
python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20 --format json
```

Prediction outputs are written under `outputs/probability/` as `probability_daily_YYYY-MM-DD.csv`. Future returns are used only as training labels, never as prediction features. See `docs/PROBABILITY_SPEC.md`.

## Point-in-Time Leakage Audit

`audit-leakage` records data snapshot metadata and checks common point-in-time risks, including financial disclosure dates, future announcement visibility, daily-bar close availability, and current-state fields in `stock_master`.

```bash
python -m ashare_alpha audit-leakage --date 2026-03-20
python -m ashare_alpha audit-leakage --date 2026-03-20 --format json
python -m ashare_alpha audit-leakage --start 2026-01-05 --end 2026-03-20
```

Audit outputs are written under `outputs/audit/leakage_DATE/` or `outputs/audit/leakage_START_END/`: `audit_report.json`, `audit_report.md`, and `data_snapshot.json`. The audit is an offline research aid; it does not fetch data, change scoring, change backtesting, or place orders. See `docs/POINT_IN_TIME_SPEC.md`.

## Daily Research Pipeline

`run-pipeline` runs the complete daily research workflow into one output directory:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20
python -m ashare_alpha run-pipeline --date 2026-03-20 --format json
python -m ashare_alpha run-pipeline --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20
python -m ashare_alpha run-pipeline --date 2026-03-20 --audit-leakage
python -m ashare_alpha run-pipeline --date 2026-03-20 --quality-report
```

Outputs are written under `outputs/pipelines/pipeline_YYYY-MM-DD/`: `manifest.json`, `pipeline_summary.md`, daily universe/factor/event/signal CSV files, an optional `probability_daily_YYYY-MM-DD.csv`, optional leakage audit files under `audit/`, optional quality files under `quality/`, and the `daily_report/` folder. Probability prediction is optional; a failed optional probability step produces `PARTIAL` unless `--require-probability` is set. Leakage audit and quality reporting are disabled by default. When enabled, error-level audit or quality issues fail the pipeline while warning/info issues allow it to continue. See `docs/PIPELINE_SPEC.md`.

## Experiment Registry

Experiment Registry records completed research runs under `outputs/experiments/`, including command args, data source/version, config hash, output directory, extracted metrics, artifacts, tags, and notes.

Record an existing run:

```bash
python -m ashare_alpha record-experiment \
  --command run-pipeline \
  --output-dir outputs/pipelines/pipeline_2026-03-20 \
  --data-dir data/sample/ashare_alpha \
  --tag mvp \
  --notes "MVP sample pipeline"
```

List, inspect, and compare experiments:

```bash
python -m ashare_alpha list-experiments
python -m ashare_alpha list-experiments --format json
python -m ashare_alpha show-experiment --id EXP_ID
python -m ashare_alpha compare-experiments --baseline EXP_A --target EXP_B
```

Pipeline and backtest runs can opt into automatic recording without changing default behavior:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20 --record-experiment --experiment-tag mvp
python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --record-experiment --experiment-tag backtest
```

Experiment comparison only reports differences in recorded metrics. It does not predict future returns, does not constitute investment advice, does not connect to brokers, and does not place orders. See `docs/EXPERIMENT_SPEC.md`.

## Sweep Runner

`run-sweep` runs offline batch experiments from a sweep YAML. It copies the base config for each variant, applies safe dot-path overrides, runs `run-pipeline`, `run-backtest`, or `train-probability-model`, records each variant in the Experiment Registry, and writes `sweep_result.json`, `sweep_summary.md`, and `metrics_table.csv`.

```bash
python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml
python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml --format json
python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_backtest_positions.yaml
python -m ashare_alpha show-sweep --path outputs/sweeps/SWEEP_ID/sweep_result.json
```

Sweeps cannot enable networking, broker connections, or live trading, and cannot write plaintext secret-like config values. See `docs/SWEEP_SPEC.md`.

## Walk-forward Validation

`run-walkforward` splits a historical period into repeated out-of-sample windows, runs `run-backtest` or `run-sweep` for each fold, records successful folds in the Experiment Registry, and writes stability metrics plus overfitting warnings.

```bash
python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml
python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml --format json
python -m ashare_alpha show-walkforward --path outputs/walkforward/WF_ID/walkforward_result.json
```

Outputs are written under `outputs/walkforward/WF_ID/`: `walkforward_result.json`, `walkforward_summary.md`, `fold_metrics.csv`, and one folder per fold. See `docs/WALKFORWARD_SPEC.md`.

## Candidate Selection

`select-candidates` ranks completed sweep, walk-forward, and experiment results for the next offline research round. It writes a JSON report, Markdown report, and CSV score table without changing strategy logic or base config files.

```bash
python -m ashare_alpha select-candidates --source outputs/walkforward/WF_ID/walkforward_result.json
python -m ashare_alpha select-candidates --source outputs/sweeps/SWEEP_ID/sweep_result.json --format json
```

`promote-candidate-config` copies a selected candidate's config snapshot to `outputs/candidate_configs/` for manual follow-up research:

```bash
python -m ashare_alpha promote-candidate-config \
  --selection outputs/candidates/selection_ID/candidate_selection.json \
  --candidate-id CANDIDATE_ID \
  --promoted-name test_candidate
```

Promotion copies only config files, refuses `configs/ashare_alpha` as a target, and does not run live trading or place orders. See `docs/CANDIDATE_SELECTION_SPEC.md`.

## Research Dashboard

`build-dashboard` scans existing research outputs and writes a static overview under `outputs/dashboard/`.

```bash
python -m ashare_alpha build-dashboard
python -m ashare_alpha build-dashboard --format json
python -m ashare_alpha show-dashboard --path outputs/dashboard/DASHBOARD_ID
```

The dashboard outputs `dashboard_index.json`, `dashboard_summary.json`, `dashboard.md`, and CSV tables for artifacts, recent experiments, top candidates, and warning items. It is read-only and does not modify research outputs, choose a live config, or place orders. See `docs/DASHBOARD_SPEC.md`.

## Research Frontend

`build-frontend` scans existing `outputs/` artifacts and writes a local read-only static HTML frontend under `outputs/frontend/`.

```bash
python -m ashare_alpha build-frontend
python -m ashare_alpha build-frontend --format json
python -m ashare_alpha build-frontend --update-latest
python -m ashare_alpha serve-frontend --dir outputs/frontend/latest
```

The generated site contains `index.html`, `assets/app.js`, `assets/style.css`, and `frontend_data.json`. Data is embedded in `assets/app.js`, so `index.html` can be opened directly with `file://` without a server. `serve-frontend` uses Python standard library `http.server`, defaults to `127.0.0.1:8765`, serves static files only, and provides no API.

The frontend is read-only: it does not call external APIs, use CDN/npm, change research logic, modify configs, connect to brokers, or place orders. See `docs/FRONTEND_SPEC.md`.

## Development

Install development dependencies:

```bash
py -3.12 -m pip install -e ".[dev]"
```

Run checks:

```bash
py -3.12 -m pytest
py -3.12 -m ruff check
```

## Risk Boundary

This project is for research and engineering only. It is not investment advice, does not promise returns, and does not provide live order submission.
