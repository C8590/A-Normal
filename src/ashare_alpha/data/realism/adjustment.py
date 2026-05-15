from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from ashare_alpha.data.realism.models import AdjustmentFactorRecord


class AdjustmentFactorSeries:
    def __init__(self, records: list[AdjustmentFactorRecord]) -> None:
        self.records = sorted(records, key=lambda item: (item.ts_code, item.adj_type, item.trade_date))
        self._by_key = {(item.ts_code, item.trade_date, item.adj_type): item for item in self.records}
        self._by_stock_type: dict[tuple[str, str], list[AdjustmentFactorRecord]] = defaultdict(list)
        for record in self.records:
            self._by_stock_type[(record.ts_code, record.adj_type)].append(record)

    def get_factor(self, ts_code: str, trade_date: date, adj_type: str = "qfq") -> float | None:
        record = self._by_key.get((ts_code, trade_date, adj_type))
        return record.adj_factor if record is not None else None

    def has_factor(self, ts_code: str, trade_date: date, adj_type: str = "qfq") -> bool:
        return self.get_factor(ts_code, trade_date, adj_type) is not None

    def factor_coverage(self, ts_code: str, adj_type: str = "qfq") -> dict[str, Any]:
        records = self._by_stock_type.get((ts_code, adj_type), [])
        dates = [item.trade_date for item in records]
        return {
            "ts_code": ts_code,
            "adj_type": adj_type,
            "row_count": len(records),
            "first_trade_date": dates[0].isoformat() if dates else None,
            "last_trade_date": dates[-1].isoformat() if dates else None,
            "factor_min": min((item.adj_factor for item in records), default=None),
            "factor_max": max((item.adj_factor for item in records), default=None),
        }
