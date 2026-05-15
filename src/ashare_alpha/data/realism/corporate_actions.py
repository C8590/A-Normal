from __future__ import annotations

from datetime import date, datetime, time

from ashare_alpha.data.realism.models import CorporateActionRecord


class CorporateActionSeries:
    def __init__(self, records: list[CorporateActionRecord]) -> None:
        self.records = sorted(records, key=lambda item: (item.ts_code, item.action_date, item.action_type))

    def actions_for_stock(self, ts_code: str) -> list[CorporateActionRecord]:
        return [item for item in self.records if item.ts_code == ts_code]

    def actions_between(self, start: date, end: date) -> list[CorporateActionRecord]:
        if start > end:
            return []
        return [item for item in self.records if start <= item.action_date <= end]

    def actions_visible_on(self, trade_date: date) -> list[CorporateActionRecord]:
        decision_time = datetime.combine(trade_date, time(15, 30))
        visible: list[CorporateActionRecord] = []
        for item in self.records:
            visible_at = item.available_at
            if visible_at is None and item.publish_date is not None:
                visible_at = datetime.combine(item.publish_date, time(0, 0))
            if visible_at is not None and visible_at <= decision_time:
                visible.append(item)
        return visible
