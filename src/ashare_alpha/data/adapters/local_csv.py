from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar, TypeVar

from pydantic import BaseModel, ValidationError

from ashare_alpha.data.adapters.base import DataAdapter
from ashare_alpha.data.models import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.data.validation import DataValidationError, DataValidationReport


ModelT = TypeVar("ModelT", bound=BaseModel)


class LocalCsvAdapter(DataAdapter):
    """Read normalized A-share research inputs from local CSV files."""

    FILES: ClassVar[dict[str, str]] = {
        "stock_master": "stock_master.csv",
        "daily_bar": "daily_bar.csv",
        "financial_summary": "financial_summary.csv",
        "announcement_event": "announcement_event.csv",
    }

    REQUIRED_FIELDS: ClassVar[dict[str, set[str]]] = {
        "stock_master": {
            "ts_code",
            "symbol",
            "name",
            "exchange",
            "board",
            "list_date",
            "is_st",
            "is_star_st",
            "is_suspended",
            "is_delisting_risk",
        },
        "daily_bar": {
            "trade_date",
            "ts_code",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "amount",
            "is_trading",
        },
        "financial_summary": {"report_date", "publish_date", "ts_code"},
        "announcement_event": {
            "event_time",
            "ts_code",
            "title",
            "source",
            "event_type",
            "event_direction",
            "event_strength",
            "event_risk_level",
        },
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    def load_stock_master(self) -> list[StockMaster]:
        return self._load_table("stock_master", StockMaster)

    def load_daily_bars(self) -> list[DailyBar]:
        return self._load_table("daily_bar", DailyBar)

    def load_financial_summary(self) -> list[FinancialSummary]:
        return self._load_table("financial_summary", FinancialSummary)

    def load_announcement_events(self) -> list[AnnouncementEvent]:
        return self._load_table("announcement_event", AnnouncementEvent)

    def validate_all(self) -> DataValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        row_counts: dict[str, int] = {}
        loaded: dict[str, list[BaseModel]] = {}

        for table_name, loader in {
            "stock_master": self.load_stock_master,
            "daily_bar": self.load_daily_bars,
            "financial_summary": self.load_financial_summary,
            "announcement_event": self.load_announcement_events,
        }.items():
            try:
                rows = loader()
            except DataValidationError as exc:
                errors.append(str(exc))
                row_counts[table_name] = 0
                continue
            loaded[table_name] = rows
            row_counts[table_name] = len(rows)
            if not rows:
                errors.append(f"{self.FILES[table_name]}: table must contain at least one row")

        stock_rows = loaded.get("stock_master")
        if stock_rows:
            stock_codes = [row.ts_code for row in stock_rows if isinstance(row, StockMaster)]
            duplicate_codes = sorted(_duplicates(stock_codes))
            if duplicate_codes:
                errors.append(f"stock_master.csv field ts_code: duplicate values: {', '.join(duplicate_codes)}")

            known_codes = set(stock_codes)
            self._validate_foreign_keys(loaded.get("daily_bar", []), known_codes, "daily_bar.csv", errors)
            self._validate_foreign_keys(
                loaded.get("financial_summary", []),
                known_codes,
                "financial_summary.csv",
                errors,
            )
            self._validate_foreign_keys(
                loaded.get("announcement_event", []),
                known_codes,
                "announcement_event.csv",
                errors,
            )

        daily_rows = [row for row in loaded.get("daily_bar", []) if isinstance(row, DailyBar)]
        duplicate_daily_keys = sorted(_duplicates(f"{row.ts_code}|{row.trade_date.isoformat()}" for row in daily_rows))
        if duplicate_daily_keys:
            errors.append(f"daily_bar.csv fields ts_code,trade_date: duplicate values: {', '.join(duplicate_daily_keys)}")

        return DataValidationReport(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            row_counts=row_counts,
        )

    def _load_table(self, table_name: str, model: type[ModelT]) -> list[ModelT]:
        path = self.data_dir / self.FILES[table_name]
        if not path.exists():
            raise DataValidationError(f"{self.FILES[table_name]}: Missing CSV file: {path}")
        if not path.is_file():
            raise DataValidationError(f"{self.FILES[table_name]}: path is not a file: {path}")

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                self._validate_header(table_name, reader.fieldnames)
                return [self._validate_row(table_name, reader.line_num, row, model) for row in reader]
        except csv.Error as exc:
            raise DataValidationError(f"{self.FILES[table_name]}: CSV read error: {exc}") from exc
        except OSError as exc:
            raise DataValidationError(f"{self.FILES[table_name]}: CSV read error: {exc}") from exc

    def _validate_header(self, table_name: str, fieldnames: list[str] | None) -> None:
        if fieldnames is None:
            raise DataValidationError(f"{self.FILES[table_name]}: CSV header is missing")

        normalized = {field.strip() for field in fieldnames if field is not None}
        missing = sorted(self.REQUIRED_FIELDS[table_name] - normalized)
        if missing:
            raise DataValidationError(
                f"{self.FILES[table_name]} header field {missing[0]}: missing required fields: {', '.join(missing)}"
            )

    def _validate_row(self, table_name: str, line_number: int, row: dict[str, str], model: type[ModelT]) -> ModelT:
        payload = {field_name: row.get(field_name, "") for field_name in model.model_fields}
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            detail = exc.errors()[0]
            field = ".".join(str(item) for item in detail.get("loc", ())) or "__root__"
            reason = detail.get("msg", "invalid value")
            raise DataValidationError(
                f"{self.FILES[table_name]} line {line_number} field {field}: {reason}"
            ) from exc

    @staticmethod
    def _validate_foreign_keys(rows: list[BaseModel], known_codes: set[str], filename: str, errors: list[str]) -> None:
        missing_codes = sorted({row.ts_code for row in rows if hasattr(row, "ts_code") and row.ts_code not in known_codes})
        if missing_codes:
            errors.append(f"{filename} field ts_code: unknown stock codes: {', '.join(missing_codes)}")


def _duplicates(values) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
