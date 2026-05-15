# DATA_SOURCE_SPEC

`ashare-alpha-lab` currently uses `local_csv` as its only available data source. The data source registry and adapter stubs added here prepare the project for future real A-share data adapters, but this task does not connect to any external service and does not fetch real data.

## Current Data Sources

List registered sources:

```bash
python -m ashare_alpha list-data-sources
python -m ashare_alpha list-data-sources --format json
```

Inspect one source:

```bash
python -m ashare_alpha inspect-data-source --name local_csv
python -m ashare_alpha inspect-data-source --name tushare_stub
```

Registered sources:

- `local_csv`: available, offline local CSV adapter.
- `tushare_stub`: stub only; does not import Tushare and does not call any external API.
- `akshare_stub`: stub only; does not import Akshare and does not call any external API.

## Why Adapter Contracts Come First

The research system depends on normalized internal models:

- `StockMaster`
- `DailyBar`
- `FinancialSummary`
- `AnnouncementEvent`

Real data vendors use different field names, adjustment methods, calendars, timestamps, and point-in-time rules. The adapter contract gives every future source a consistent target before it can feed the universe, factor, event, signal, backtest, report, probability, or pipeline modules.

## Metadata And Capabilities

Each registered source has `DataSourceMetadata`:

- `name`
- `display_name`
- `description`
- `adapter_class`
- `status`: `available`, `stub`, or `disabled`
- `capabilities`

Capabilities include support flags for stock master, daily bars, financial summaries, announcements, adjusted prices, minute bars, point-in-time data, incremental updates, network requirement, API key requirement, and live-trading status.

For safety, every future external market-data source should set:

- `requires_network=true`
- `requires_api_key=true` when credentials are needed
- `is_live_trading_source=false`

The current project must not treat data sources as broker or order-routing integrations.

## Field Mapping

`FieldMapping` maps vendor field names to internal model fields.

Example:

```python
mapping = FieldMapping(
    source_to_internal={
        "code": "ts_code",
        "date": "trade_date",
        "vol": "volume",
    },
    required_internal_fields=("ts_code", "trade_date", "volume"),
)
```

`apply_mapping(row)` returns a normalized dict. `validate_required_fields(row)` raises a clear error when required internal fields are absent or empty.

## Requirements For Future Real Data Adapters

Before a real external adapter is enabled, it must satisfy:

1. Field mapping into internal models.
2. `validate_all()` with clear validation errors.
3. Point-in-time protection to avoid look-ahead leakage.
4. Data version and refresh metadata.
5. No API keys or credentials committed to code, configs, tests, or docs.
6. No direct path from data adapter to live trading or broker submission.
7. Tests proving the adapter follows `DataAdapter` contract.

## Stub Boundary

`TushareAdapterStub` and `AkshareAdapterStub` intentionally raise `NotImplementedError` for every load method. The message states that the source is still a stub and this task does not call external APIs.

The stubs do not import vendor SDKs, do not import networking libraries, and do not make network requests.

## Risk Boundary

The current system remains a research and backtesting system. It is not investment advice, does not promise returns, does not automatically place orders, and does not connect to broker APIs.
