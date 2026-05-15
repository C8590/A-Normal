# Source Runtime Spec

`source profile` is the runtime configuration for an external data source adapter. It describes the source name, display name, runtime mode, offline fixture or cache location, field-mapping YAML, materialized output root, and security requirements. Profiles live under `configs/ashare_alpha/source_profiles/`.

The runtime is still offline-first. It does not import vendor SDKs, does not call external APIs, does not scrape websites, does not connect to brokers, and does not place orders.

## Modes

- `offline_replay`: reads local external-source fixture CSVs, validates the external contract, converts them through the mapping YAML, and writes the standard four-table directory.
- `cache_only`: reads an existing local cache that already contains `stock_master.csv`, `daily_bar.csv`, `financial_summary.csv`, and `announcement_event.csv`. It never downloads missing data.
- `live_disabled`: placeholder for future real API adapters. It is intentionally non-runnable.

Default security config keeps `offline_mode=true` and `allow_network=false`. This prevents accidental network use while adapter contracts, conversion, validation, and quality checks are developed locally.

## Runtime Safety

Every future network-capable adapter must call `SourceRuntimeContext.assert_can_attempt_network()`, which delegates to `NetworkGuard.assert_network_allowed()`, before any network access. Current adapters only call `assert_can_run_offline()` and read local files.

API keys must be referenced by environment variable name only. Profiles must not contain raw tokens or secrets.

## Commands

List profiles:

```bash
python -m ashare_alpha list-source-profiles
python -m ashare_alpha list-source-profiles --format json
```

Inspect one profile and the active security summary:

```bash
python -m ashare_alpha inspect-source-profile \
  --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml
```

Materialize an offline source into standard four-table CSV data:

```bash
python -m ashare_alpha materialize-source \
  --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml \
  --data-version contract_sample \
  --quality-report
```

The output directory is:

```text
data/materialized/{source_name}/{data_version}/
```

The command writes the four standard CSV files, `materialization_result.json`, and, with `--quality-report`, `quality_report.json`, `quality_report.md`, and `quality_issues.csv`.

## Recommended Flow

Materialize:

```bash
python -m ashare_alpha materialize-source \
  --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml \
  --data-version contract_sample \
  --quality-report
```

Validate and import:

```bash
python -m ashare_alpha validate-data \
  --data-dir data/materialized/tushare_like_offline/contract_sample

python -m ashare_alpha import-data \
  --source-name tushare_like_offline \
  --source-data-dir data/materialized/tushare_like_offline/contract_sample \
  --data-version contract_sample \
  --overwrite \
  --quality-report
```

Run the research pipeline on imported data:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --data-dir data/imports/tushare_like_offline/contract_sample \
  --audit-leakage \
  --quality-report \
  --check-security
```

This remains a research-only workflow. It does not fetch real data, use real API keys, submit live orders, or promise returns.
