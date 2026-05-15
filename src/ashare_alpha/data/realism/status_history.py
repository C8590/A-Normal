from __future__ import annotations

from collections import defaultdict
from datetime import date

from ashare_alpha.data.realism.models import StockStatusHistoryRecord


class StockStatusHistory:
    def __init__(self, records: list[StockStatusHistoryRecord]) -> None:
        self.records = sorted(records, key=lambda item: (item.ts_code, item.effective_start, item.effective_end or date.max))
        self._by_stock: dict[str, list[StockStatusHistoryRecord]] = defaultdict(list)
        for record in self.records:
            self._by_stock[record.ts_code].append(record)

    def get_status(self, ts_code: str, on_date: date) -> StockStatusHistoryRecord | None:
        matches = [
            record
            for record in self._by_stock.get(ts_code, [])
            if record.effective_start <= on_date and (record.effective_end is None or on_date <= record.effective_end)
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.effective_start)[-1]

    def is_st(self, ts_code: str, on_date: date) -> bool | None:
        record = self.get_status(ts_code, on_date)
        return (record.is_st or record.is_star_st) if record is not None else None

    def is_suspended(self, ts_code: str, on_date: date) -> bool | None:
        record = self.get_status(ts_code, on_date)
        return record.is_suspended if record is not None else None

    def board_on(self, ts_code: str, on_date: date) -> str | None:
        record = self.get_status(ts_code, on_date)
        return record.board if record is not None else None

    def industry_on(self, ts_code: str, on_date: date) -> str | None:
        record = self.get_status(ts_code, on_date)
        return record.industry if record is not None else None

    def listing_status_on(self, ts_code: str, on_date: date) -> str | None:
        record = self.get_status(ts_code, on_date)
        return record.listing_status if record is not None else None
