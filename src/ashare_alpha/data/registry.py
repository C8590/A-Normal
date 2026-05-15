from __future__ import annotations

from ashare_alpha.data.sources import DataSourceCapabilities, DataSourceMetadata


class DataSourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, DataSourceMetadata] = {}

    def register(self, metadata: DataSourceMetadata) -> None:
        if metadata.name in self._sources:
            raise ValueError(f"Data source already registered: {metadata.name}")
        self._sources[metadata.name] = metadata

    def list_sources(self) -> list[DataSourceMetadata]:
        return [self._sources[name] for name in sorted(self._sources)]

    def get_source(self, name: str) -> DataSourceMetadata:
        try:
            return self._sources[name]
        except KeyError as exc:
            raise ValueError(f"Unknown data source: {name}") from exc

    def get_available_sources(self) -> list[DataSourceMetadata]:
        return [source for source in self.list_sources() if source.status == "available"]

    def get_stub_sources(self) -> list[DataSourceMetadata]:
        return [source for source in self.list_sources() if source.status == "stub"]

    def validate_source_exists(self, name: str) -> None:
        self.get_source(name)


def create_default_data_source_registry() -> DataSourceRegistry:
    registry = DataSourceRegistry()
    registry.register(
        DataSourceMetadata(
            name="local_csv",
            display_name="Local CSV",
            description="本地标准化 CSV 数据源，用于离线样例研究和测试。",
            adapter_class="ashare_alpha.data.adapters.local_csv.LocalCsvAdapter",
            capabilities=DataSourceCapabilities(
                supports_stock_master=True,
                supports_daily_bar=True,
                supports_financial_summary=True,
                supports_announcement_event=True,
                supports_adjusted_price=False,
                supports_minute_bar=False,
                supports_point_in_time=True,
                supports_incremental_update=False,
                requires_network=False,
                requires_api_key=False,
                is_live_trading_source=False,
            ),
            status="available",
        )
    )
    registry.register(
        DataSourceMetadata(
            name="tushare_stub",
            display_name="Tushare Stub",
            description="Tushare 数据源占位 Adapter；当前不会联网，也不会读取真实数据。",
            adapter_class="ashare_alpha.data.adapters.stub_external.TushareAdapterStub",
            capabilities=_external_stub_capabilities(),
            status="stub",
        )
    )
    registry.register(
        DataSourceMetadata(
            name="akshare_stub",
            display_name="Akshare Stub",
            description="Akshare 数据源占位 Adapter；当前不会联网，也不会读取真实数据。",
            adapter_class="ashare_alpha.data.adapters.stub_external.AkshareAdapterStub",
            capabilities=_external_stub_capabilities(),
            status="stub",
        )
    )
    return registry


def get_default_data_source_registry() -> DataSourceRegistry:
    return create_default_data_source_registry()


def _external_stub_capabilities() -> DataSourceCapabilities:
    return DataSourceCapabilities(
        supports_stock_master=True,
        supports_daily_bar=True,
        supports_financial_summary=True,
        supports_announcement_event=True,
        supports_adjusted_price=True,
        supports_minute_bar=False,
        supports_point_in_time=False,
        supports_incremental_update=True,
        requires_network=True,
        requires_api_key=True,
        is_live_trading_source=False,
    )
