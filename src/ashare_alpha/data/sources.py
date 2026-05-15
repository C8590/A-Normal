from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DataSourceStatus = Literal["available", "stub", "disabled"]


class DataSourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataSourceCapabilities(DataSourceModel):
    supports_stock_master: bool
    supports_daily_bar: bool
    supports_financial_summary: bool
    supports_announcement_event: bool
    supports_adjusted_price: bool
    supports_minute_bar: bool
    supports_point_in_time: bool
    supports_incremental_update: bool
    requires_network: bool
    requires_api_key: bool
    is_live_trading_source: bool


class DataSourceMetadata(DataSourceModel):
    name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    adapter_class: str = Field(min_length=1)
    capabilities: DataSourceCapabilities
    status: DataSourceStatus
