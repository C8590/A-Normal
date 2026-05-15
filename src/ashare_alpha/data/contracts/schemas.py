from __future__ import annotations

from ashare_alpha.data.contracts.models import ExternalDatasetContract


def get_external_contracts(source_name: str) -> list[ExternalDatasetContract]:
    normalized = source_name.strip().lower()
    if normalized == "tushare_like":
        return _tushare_like_contracts()
    if normalized == "akshare_like":
        return _akshare_like_contracts()
    raise ValueError(f"Unsupported external source contract: {source_name}")


def _contract(
    source_name: str,
    dataset_name: str,
    required_fields: list[str],
    optional_fields: list[str],
    target_dataset_name: str,
    description: str,
) -> ExternalDatasetContract:
    return ExternalDatasetContract(
        source_name=source_name,
        dataset_name=dataset_name,
        required_fields=required_fields,
        optional_fields=optional_fields,
        target_dataset_name=target_dataset_name,
        description=description,
    )


def _tushare_like_contracts() -> list[ExternalDatasetContract]:
    source = "tushare_like"
    return [
        _contract(
            source,
            "stock_basic",
            ["ts_code", "symbol", "name", "exchange", "list_date"],
            ["industry", "market", "delist_date", "is_hs"],
            "stock_master",
            "Tushare-like stock master fixture.",
        ),
        _contract(
            source,
            "daily",
            ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "vol", "amount"],
            ["pct_chg", "change"],
            "daily_bar",
            "Tushare-like daily bar fixture.",
        ),
        _contract(
            source,
            "fina_indicator",
            ["ts_code", "end_date", "ann_date"],
            [
                "revenue_yoy",
                "netprofit_yoy",
                "roe",
                "grossprofit_margin",
                "debt_to_assets",
                "ocf_to_profit",
                "goodwill_to_equity",
            ],
            "financial_summary",
            "Tushare-like financial indicator fixture.",
        ),
        _contract(
            source,
            "announcements",
            ["ts_code", "ann_time", "title"],
            ["source", "event_type", "content"],
            "announcement_event",
            "Tushare-like announcement fixture.",
        ),
    ]


def _akshare_like_contracts() -> list[ExternalDatasetContract]:
    source = "akshare_like"
    return [
        _contract(
            source,
            "stock_info",
            ["code", "name", "exchange", "board", "list_date"],
            ["industry", "delist_date"],
            "stock_master",
            "AkShare-like stock master fixture.",
        ),
        _contract(
            source,
            "stock_zh_a_hist",
            ["code", "date", "open", "close", "high", "low", "volume", "amount"],
            ["turnover_rate"],
            "daily_bar",
            "AkShare-like daily history fixture.",
        ),
        _contract(
            source,
            "financial_abstract",
            ["code", "report_date", "publish_date"],
            [
                "revenue_yoy",
                "net_profit_yoy",
                "roe",
                "gross_margin",
                "debt_to_asset",
                "operating_cashflow_to_profit",
                "goodwill_to_equity",
            ],
            "financial_summary",
            "AkShare-like financial abstract fixture.",
        ),
        _contract(
            source,
            "stock_notice",
            ["code", "notice_time", "title"],
            ["source", "notice_type", "content"],
            "announcement_event",
            "AkShare-like stock notice fixture.",
        ),
    ]
