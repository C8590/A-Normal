from __future__ import annotations

from ashare_alpha.data.adapters import AkshareAdapterStub, DataAdapter, ExternalDataAdapterStub, LocalCsvAdapter, TushareAdapterStub
from ashare_alpha.data.field_mapping import DAILY_BAR_REQUIRED_FIELDS, FieldMapping
from ashare_alpha.data.models import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.data.registry import DataSourceRegistry, get_default_data_source_registry
from ashare_alpha.data.sources import DataSourceCapabilities, DataSourceMetadata
from ashare_alpha.data.validation import DataValidationError, DataValidationReport

__all__ = [
    "AkshareAdapterStub",
    "AnnouncementEvent",
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
    "StockMaster",
    "TushareAdapterStub",
    "get_default_data_source_registry",
]
