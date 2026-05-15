# External Cache Store Spec

## 1. Purpose

The external cache store prepares `ashare-alpha-lab` for future real data adapters without enabling network access today.

Current behavior is fully offline:

- copy local external fixtures into a raw cache;
- record `cache_manifest.json`;
- validate raw cache files against the external source contract;
- materialize raw cache files into the standard four local CSV tables;
- validate normalized tables with `LocalCsvAdapter`;
- feed normalized tables into `import-data`, `quality-report`, `audit-leakage`, and `run-pipeline`.

It does not call vendor APIs, scrape websites, read real API keys, connect to brokers, or place orders.

## 2. Directory Layout

Default cache root:

```text
data/cache/external/{source_name}/{cache_version}/
  cache_manifest.json
  validation_report.json
  conversion_result.json        # after materialize-cache
  raw/
    stock_basic.csv
    daily.csv
    fina_indicator.csv
    announcements.csv
  normalized/
    stock_master.csv
    daily_bar.csv
    financial_summary.csv
    announcement_event.csv
```

AkShare-like fixtures use their own raw filenames:

```text
raw/
  stock_info.csv
  stock_zh_a_hist.csv
  financial_abstract.csv
  stock_notice.csv
```

`data/cache/` is ignored by git because it is a local runtime cache.

## 3. Manifest

`cache_manifest.json` contains:

- `cache_id`
- `source_name`
- `cache_version`
- `created_at`
- `updated_at`
- `cache_dir`
- `raw_dir`
- `normalized_dir`
- `mapping_path`
- `raw_files`
- `normalized_files`
- `raw_contract_passed`
- `normalized_validation_passed`
- `normalized_row_counts`
- `validation_errors`
- `validation_warnings`
- `status`
- `summary`

Statuses:

- `RAW_CACHED`: raw external fixture files are cached and contract-validated.
- `NORMALIZED`: normalized four-table CSVs exist and pass local validation.
- `FAILED`: cache or materialization validation failed.

## 4. Commands

Create raw cache from offline fixture:

```bash
python -m ashare_alpha cache-source-fixture \
  --source-name tushare_like \
  --fixture-dir tests/fixtures/external_sources/tushare_like \
  --cache-version contract_sample
```

List caches:

```bash
python -m ashare_alpha list-caches
python -m ashare_alpha list-caches --source-name tushare_like --format json
```

Inspect one cache:

```bash
python -m ashare_alpha inspect-cache \
  --source-name tushare_like \
  --cache-version contract_sample
```

Materialize raw cache into standard tables:

```bash
python -m ashare_alpha materialize-cache \
  --source-name tushare_like \
  --cache-version contract_sample
```

Validate normalized output:

```bash
python -m ashare_alpha validate-data \
  --data-dir data/cache/external/tushare_like/contract_sample/normalized
```

Import normalized output:

```bash
python -m ashare_alpha import-data \
  --source-name tushare_like \
  --source-data-dir data/cache/external/tushare_like/contract_sample/normalized \
  --data-version contract_sample \
  --quality-report
```

Run the research pipeline on imported data:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --data-dir data/imports/tushare_like/contract_sample \
  --audit-leakage \
  --quality-report \
  --check-security
```

## 5. Safety

Cache commands load `SecurityConfig` and require:

- `allow_network=false`
- `allow_broker_connections=false`
- `allow_live_trading=false`

`offline_mode=true` is compatible with cache operations because they only read and write local files. Future network modes must be implemented separately and pass through the security layer before any network access.

## 6. Future Adapter Flow

Future real data adapters should follow this path:

```text
external source config
  -> network disabled by default
  -> API response saved to raw cache when explicitly allowed in a future version
  -> raw cache validated
  -> normalized four-table cache
  -> import-data
  -> audit-leakage / quality-report / run-pipeline
```

This keeps research logic unchanged and makes every data handoff inspectable.
