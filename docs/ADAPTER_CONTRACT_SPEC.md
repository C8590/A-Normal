# Adapter Contract Spec

## 1. Why Offline Contract Tests Come First

Future real data-source adapters need a stable contract before they touch vendor SDKs or live networks. This project therefore tests external-source shapes with local fixture CSV files first. The fixture contract checks that the expected columns exist, and the converter proves those external columns can become the four internal standard CSV tables.

This task does not import Tushare or AkShare, does not call external APIs, does not scrape websites, and does not connect to brokers.

## 2. Fixture Directory Layout

Tushare-like fixtures:

```text
tests/fixtures/external_sources/tushare_like/
  stock_basic.csv
  daily.csv
  fina_indicator.csv
  announcements.csv
```

AkShare-like fixtures:

```text
tests/fixtures/external_sources/akshare_like/
  stock_info.csv
  stock_zh_a_hist.csv
  financial_abstract.csv
  stock_notice.csv
```

These files are synthetic samples for adapter development. They are not downloaded from the real services.

## 3. validate-adapter-contract

Validate an external fixture directory against the offline contract:

```bash
python -m ashare_alpha validate-adapter-contract --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like
python -m ashare_alpha validate-adapter-contract --source-name akshare_like --fixture-dir tests/fixtures/external_sources/akshare_like --format json
```

The command writes `contract_report.json` and `contract_report.md` under `outputs/contracts/{source_name}` unless `--output-dir` is provided. Missing required fields are errors. Missing optional fields are info. Empty CSV files are warnings.

## 4. convert-source-fixture

Convert a valid external fixture directory into the internal four-table CSV format:

```bash
python -m ashare_alpha convert-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --output-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha convert-source-fixture --source-name akshare_like --fixture-dir tests/fixtures/external_sources/akshare_like --output-dir data/imports/akshare_like/contract_sample
```

The converter first runs the contract validator. If required fields are missing, conversion is skipped. After writing the standard CSVs, it runs `LocalCsvAdapter.validate_all()`. If local validation fails, the generated files remain for inspection and the command returns non-zero.

## 5. Mapping YAML Structure

Mapping templates live under `configs/ashare_alpha/data_sources/`:

```text
configs/ashare_alpha/data_sources/tushare_like_mapping.yaml
configs/ashare_alpha/data_sources/akshare_like_mapping.yaml
```

Each file has:

```yaml
source_name: tushare_like
datasets:
  daily:
    target_dataset: daily_bar
    field_mapping:
      trade_date: trade_date
      ts_code: ts_code
      vol: volume
    defaults:
      is_trading: true
      limit_up: null
```

`field_mapping` maps external column names to internal column names. `defaults` fills internal fields when the mapped value is missing or blank.

## 6. Standardization Rules

`ts_code`:

- `600001.SH` stays `600001.SH`.
- `600001` infers `600001.SH` from exchange or prefix.
- `000001` infers `000001.SZ`.
- `688001` infers `688001.SH`.
- `920001` infers `920001.BJ`.

`exchange`:

- `SSE`, `SH`, `上海`, and `sse` become `sse`.
- `SZSE`, `SZ`, `深圳`, and `szse` become `szse`.
- `BSE`, `BJ`, `北交所`, and `bse` become `bse`.

`board`:

- `主板`, `main`, and `主板A股` become `main`.
- `创业板` and `chinext` become `chinext`.
- `科创板` and `star` become `star`.
- `北交所` and `bse` become `bse`.
- If needed, the converter infers board from `ts_code` prefixes.

`date`:

- `YYYYMMDD` becomes `YYYY-MM-DD`.
- `YYYY-MM-DD` stays unchanged.
- Datetime fields are normalized to ISO datetime where possible.

## 7. Importing Converted Data

After conversion, the output directory contains:

```text
stock_master.csv
daily_bar.csv
financial_summary.csv
announcement_event.csv
```

The directory can enter the existing workflow:

```bash
python -m ashare_alpha validate-data --data-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha quality-report --data-dir data/imports/tushare_like/contract_sample
python -m ashare_alpha import-data --source-name tushare_like --source-data-dir data/imports/tushare_like/contract_sample --data-version contract_sample --overwrite
```

## 8. Boundaries

This contract layer is offline only. It does not perform live trading, broker integration, high-frequency trading, web scraping, or real API access. It does not contain API keys or credentials.

The system is for research, backtesting, signal generation, and reporting only. It does not automatically place orders, does not guarantee returns, and does not constitute investment advice.
