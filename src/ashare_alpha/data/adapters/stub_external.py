from __future__ import annotations

from ashare_alpha.data.adapters.base import DataAdapter
from ashare_alpha.data.models import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.data.validation import DataValidationReport


STUB_MESSAGE = "该数据源仍是 stub，本任务不调用外部 API。"


class ExternalDataAdapterStub(DataAdapter):
    """Placeholder for future external data adapters; it never calls the network."""

    source_name = "external_stub"

    def load_stock_master(self) -> list[StockMaster]:
        raise NotImplementedError(STUB_MESSAGE)

    def load_daily_bars(self) -> list[DailyBar]:
        raise NotImplementedError(STUB_MESSAGE)

    def load_financial_summary(self) -> list[FinancialSummary]:
        raise NotImplementedError(STUB_MESSAGE)

    def load_announcement_events(self) -> list[AnnouncementEvent]:
        raise NotImplementedError(STUB_MESSAGE)

    def validate_all(self) -> DataValidationReport:
        raise NotImplementedError(STUB_MESSAGE)


class TushareAdapterStub(ExternalDataAdapterStub):
    source_name = "tushare_stub"


class AkshareAdapterStub(ExternalDataAdapterStub):
    source_name = "akshare_stub"
