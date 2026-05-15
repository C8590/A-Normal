from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from ashare_alpha.data.realism.models import (
    AdjustmentFactorRecord,
    CorporateActionRecord,
    StockStatusHistoryRecord,
    TradeCalendarRecord,
)
from ashare_alpha.data.validation import DataValidationError


ModelT = TypeVar("ModelT", bound=BaseModel)


class RealismDataBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_calendar: list[TradeCalendarRecord]
    stock_status_history: list[StockStatusHistoryRecord]
    adjustment_factors: list[AdjustmentFactorRecord]
    corporate_actions: list[CorporateActionRecord]
    missing_optional_files: list[str]


class OptionalRealismDataLoader:
    FILES: ClassVar[dict[str, str]] = {
        "trade_calendar": "trade_calendar.csv",
        "stock_status_history": "stock_status_history.csv",
        "adjustment_factors": "adjustment_factor.csv",
        "corporate_actions": "corporate_action.csv",
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.missing_optional_files: list[str] = []

    def load_trade_calendar(self) -> list[TradeCalendarRecord]:
        return self._load_optional_table("trade_calendar", TradeCalendarRecord)

    def load_stock_status_history(self) -> list[StockStatusHistoryRecord]:
        return self._load_optional_table("stock_status_history", StockStatusHistoryRecord)

    def load_adjustment_factors(self) -> list[AdjustmentFactorRecord]:
        return self._load_optional_table("adjustment_factors", AdjustmentFactorRecord)

    def load_corporate_actions(self) -> list[CorporateActionRecord]:
        return self._load_optional_table("corporate_actions", CorporateActionRecord)

    def load_all(self) -> RealismDataBundle:
        self.missing_optional_files = []
        return RealismDataBundle(
            trade_calendar=self.load_trade_calendar(),
            stock_status_history=self.load_stock_status_history(),
            adjustment_factors=self.load_adjustment_factors(),
            corporate_actions=self.load_corporate_actions(),
            missing_optional_files=list(self.missing_optional_files),
        )

    def _load_optional_table(self, table_name: str, model: type[ModelT]) -> list[ModelT]:
        filename = self.FILES[table_name]
        path = self.data_dir / filename
        if not path.exists():
            if filename not in self.missing_optional_files:
                self.missing_optional_files.append(filename)
            return []
        if not path.is_file():
            raise DataValidationError(f"{filename}: path is not a file: {path}")
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames is None:
                    raise DataValidationError(f"{filename}: CSV header is missing")
                return [self._validate_row(filename, reader.line_num, row, model) for row in reader]
        except csv.Error as exc:
            raise DataValidationError(f"{filename}: CSV read error: {exc}") from exc
        except OSError as exc:
            raise DataValidationError(f"{filename}: CSV read error: {exc}") from exc

    @staticmethod
    def _validate_row(filename: str, line_number: int, row: dict[str, str], model: type[ModelT]) -> ModelT:
        payload = {field_name: row.get(field_name, "") for field_name in model.model_fields}
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            detail = exc.errors()[0]
            field = ".".join(str(item) for item in detail.get("loc", ())) or "__root__"
            reason = detail.get("msg", "invalid value")
            raise DataValidationError(f"{filename} line {line_number} field {field}: {reason}") from exc
