from __future__ import annotations

from ashare_alpha.data import DataSourceCapabilities, DataSourceMetadata, get_default_data_source_registry


def test_data_source_capabilities_validate() -> None:
    capabilities = DataSourceCapabilities(
        supports_stock_master=True,
        supports_daily_bar=True,
        supports_financial_summary=False,
        supports_announcement_event=False,
        supports_adjusted_price=False,
        supports_minute_bar=False,
        supports_point_in_time=True,
        supports_incremental_update=False,
        requires_network=False,
        requires_api_key=False,
        is_live_trading_source=False,
    )

    assert capabilities.supports_stock_master is True


def test_local_csv_metadata_is_available() -> None:
    source = get_default_data_source_registry().get_source("local_csv")

    assert source.status == "available"
    assert source.adapter_class.endswith("LocalCsvAdapter")


def test_tushare_stub_metadata_is_stub() -> None:
    source = get_default_data_source_registry().get_source("tushare_stub")

    assert source.status == "stub"
    assert source.capabilities.requires_network is True


def test_metadata_model_validates() -> None:
    metadata = DataSourceMetadata(
        name="test",
        display_name="Test",
        description="测试数据源",
        adapter_class="example.Adapter",
        capabilities=get_default_data_source_registry().get_source("local_csv").capabilities,
        status="disabled",
    )

    assert metadata.status == "disabled"
