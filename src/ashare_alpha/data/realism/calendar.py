from __future__ import annotations

from datetime import date

from ashare_alpha.data.realism.models import TradeCalendarRecord


class TradingCalendar:
    def __init__(self, records: list[TradeCalendarRecord]) -> None:
        self.records = sorted(records, key=lambda item: (item.calendar_date, item.exchange))
        self._by_key = {(item.exchange, item.calendar_date): item for item in self.records}

    def is_open(self, calendar_date: date, exchange: str = "all") -> bool | None:
        record = self._record_for(calendar_date, exchange)
        return record.is_open if record is not None else None

    def previous_open_date(self, calendar_date: date, exchange: str = "all") -> date | None:
        record = self._record_for(calendar_date, exchange)
        if record is not None:
            return record.previous_open_date
        candidates = [item.calendar_date for item in self._records_for_exchange(exchange) if item.is_open and item.calendar_date < calendar_date]
        return candidates[-1] if candidates else None

    def next_open_date(self, calendar_date: date, exchange: str = "all") -> date | None:
        record = self._record_for(calendar_date, exchange)
        if record is not None:
            return record.next_open_date
        candidates = [item.calendar_date for item in self._records_for_exchange(exchange) if item.is_open and item.calendar_date > calendar_date]
        return candidates[0] if candidates else None

    def open_dates(self, start: date, end: date, exchange: str = "all") -> list[date]:
        if start > end:
            return []
        return [
            item.calendar_date
            for item in self._records_for_exchange(exchange)
            if item.is_open and start <= item.calendar_date <= end
        ]

    def _record_for(self, calendar_date: date, exchange: str) -> TradeCalendarRecord | None:
        exact = self._by_key.get((exchange, calendar_date))
        if exact is not None:
            return exact
        return self._by_key.get(("all", calendar_date))

    def _records_for_exchange(self, exchange: str) -> list[TradeCalendarRecord]:
        exact_dates = {item.calendar_date for item in self.records if item.exchange == exchange}
        selected: list[TradeCalendarRecord] = []
        for item in self.records:
            if item.exchange == exchange or (item.exchange == "all" and item.calendar_date not in exact_dates):
                selected.append(item)
        return selected
