from __future__ import annotations

from ashare_alpha.data.adapters import AkshareAdapterStub, DataAdapter, ExternalDataAdapterStub, LocalCsvAdapter, TushareAdapterStub
from ashare_alpha.data.field_mapping import DAILY_BAR_REQUIRED_FIELDS, FieldMapping
from ashare_alpha.data.models import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.data.realism import (
    AdjustmentFactorRecord,
    AdjustmentFactorSeries,
    CorporateActionRecord,
    CorporateActionSeries,
    OptionalRealismDataLoader,
    RealismDataBundle,
    StockStatusHistory,
    StockStatusHistoryRecord,
    TradeCalendarRecord,
    TradingCalendar,
)
from ashare_alpha.data.registry import DataSourceRegistry, get_default_data_source_registry
from ashare_alpha.data.sources import DataSourceCapabilities, DataSourceMetadata
from ashare_alpha.data.validation import DataValidationError, DataValidationReport

__all__ = [
    "AkshareAdapterStub",
    "AdjustmentFactorRecord",
    "AdjustmentFactorSeries",
    "AnnouncementEvent",
    "CorporateActionRecord",
    "CorporateActionSeries",
    "DAILY_BAR_REQUIRED_FIELDS",
    "DailyBar",
    "DataAdapter",
    "DataSourceCapabilities",
    "DataSourceMetadata",
    "DataSourceRegistry",
    "DataValidationError",
    "DataValidationReport",
    "ExternalDataAdapterStub",
    "FieldMapping",
    "FinancialSummary",
    "LocalCsvAdapter",
    "OptionalRealismDataLoader",
    "RealismDataBundle",
    "StockStatusHistory",
    "StockStatusHistoryRecord",
    "StockMaster",
    "TushareAdapterStub",
    "TradeCalendarRecord",
    "TradingCalendar",
    "get_default_data_source_registry",
]
