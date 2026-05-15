from __future__ import annotations

from abc import ABC, abstractmethod
import csv
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel, ValidationError

from a_normal.data.models import (
    AnnouncementEvent,
    DailyBar,
    FinancialSummary,
    StockMaster,
)


TModel = TypeVar("TModel", bound=BaseModel)
DEFAULT_SAMPLE_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "sample"


class DataAdapter(ABC):
    @abstractmethod
    def load_stock_master(self) -> list[StockMaster]:
        raise NotImplementedError

    @abstractmethod
    def load_daily_bars(self) -> list[DailyBar]:
        raise NotImplementedError

    @abstractmethod
    def load_financial_summaries(self) -> list[FinancialSummary]:
        raise NotImplementedError

    @abstractmethod
    def load_announcement_events(self) -> list[AnnouncementEvent]:
        raise NotImplementedError


class LocalCsvAdapter(DataAdapter):
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else DEFAULT_SAMPLE_DATA_DIR

    def load_stock_master(self) -> list[StockMaster]:
        return self._load_csv("stock_master.csv", StockMaster)

    def load_daily_bars(self) -> list[DailyBar]:
        bars = self._load_csv("daily_bar.csv", DailyBar)
        self._validate_stock_codes(bars, source="daily_bar.csv")
        return bars

    def load_financial_summaries(self) -> list[FinancialSummary]:
        summaries = self._load_csv("financial_summary.csv", FinancialSummary)
        self._validate_stock_codes(summaries, source="financial_summary.csv")
        return summaries

    def load_announcement_events(self) -> list[AnnouncementEvent]:
        events = self._load_csv("announcement_event.csv", AnnouncementEvent)
        self._validate_stock_codes(events, source="announcement_event.csv")
        return events

    def _load_csv(self, filename: str, model: type[TModel]) -> list[TModel]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file is empty or missing a header: {path}")

            rows: list[TModel] = []
            for line_number, row in enumerate(reader, start=2):
                try:
                    rows.append(model.model_validate(row))
                except ValidationError as exc:
                    raise ValueError(f"Invalid row in {path} at line {line_number}: {exc}") from exc
            return rows

    def _validate_stock_codes(self, rows: Iterable[BaseModel], source: str) -> None:
        known_codes = {item.stock_code for item in self.load_stock_master()}
        missing = sorted(
            {str(getattr(row, "stock_code")) for row in rows if getattr(row, "stock_code") not in known_codes}
        )
        if missing:
            missing_codes = ", ".join(missing)
            raise ValueError(f"{source} references unknown stock_code: {missing_codes}")
