from __future__ import annotations

from abc import ABC, abstractmethod

from ashare_alpha.data.models import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.data.validation import DataValidationReport


class DataAdapter(ABC):
    """Abstract data adapter for normalized A-share research inputs."""

    @abstractmethod
    def load_stock_master(self) -> list[StockMaster]:
        raise NotImplementedError

    @abstractmethod
    def load_daily_bars(self) -> list[DailyBar]:
        raise NotImplementedError

    @abstractmethod
    def load_financial_summary(self) -> list[FinancialSummary]:
        raise NotImplementedError

    @abstractmethod
    def load_announcement_events(self) -> list[AnnouncementEvent]:
        raise NotImplementedError

    @abstractmethod
    def validate_all(self) -> DataValidationReport:
        raise NotImplementedError
