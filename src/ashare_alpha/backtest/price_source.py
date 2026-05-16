from __future__ import annotations

from datetime import date
from typing import Any

from ashare_alpha.adjusted import AdjustedDailyBarBuilder
from ashare_alpha.adjusted.models import AdjustedDailyBarRecord
from ashare_alpha.backtest.models import validate_backtest_price_source
from ashare_alpha.data import DailyBar
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord


class BacktestPriceSourceProvider:
    def __init__(
        self,
        daily_bars: list[DailyBar],
        adjustment_factors: list[AdjustmentFactorRecord] | None = None,
        corporate_actions: list[CorporateActionRecord] | None = None,
        price_source: str = "raw",
    ) -> None:
        validate_backtest_price_source(price_source)
        self.daily_bars = daily_bars
        self.adjustment_factors = adjustment_factors or []
        self.corporate_actions = corporate_actions or []
        self.price_source = price_source
        self._raw_by_key = {(bar.ts_code, bar.trade_date): bar for bar in daily_bars}
        self._adjusted_by_key: dict[tuple[str, date], AdjustedDailyBarRecord] = {}
        self._adjusted_records_count = 0
        self._adjusted_invalid_count = 0
        self._missing_adjusted_count = 0
        if price_source != "raw" and daily_bars:
            start_date = min(bar.trade_date for bar in daily_bars)
            end_date = max(bar.trade_date for bar in daily_bars)
            records, _summary = AdjustedDailyBarBuilder(
                daily_bars=daily_bars,
                adjustment_factors=self.adjustment_factors,
                corporate_actions=self.corporate_actions,
                adj_type=price_source,
            ).build_for_range(start_date, end_date)
            self._adjusted_by_key = {(record.ts_code, record.trade_date): record for record in records}
            self._adjusted_records_count = len(records)
            self._adjusted_invalid_count = sum(1 for record in records if not self._is_valid_adjusted_record(record))

    def get_execution_bar(self, ts_code: str, trade_date: date) -> DailyBar | None:
        return self.get_raw_bar(ts_code, trade_date)

    def get_raw_bar(self, ts_code: str, trade_date: date) -> DailyBar | None:
        return self._raw_by_key.get((ts_code, trade_date))

    def get_valuation_price(self, ts_code: str, trade_date: date) -> float | None:
        if self.price_source == "raw":
            bar = self.get_raw_bar(ts_code, trade_date)
            return bar.close if bar is not None else None
        record = self._adjusted_by_key.get((ts_code, trade_date))
        if record is None or not self._is_valid_adjusted_record(record):
            self._missing_adjusted_count += 1
            return None
        return record.adj_close

    def get_target_position_price(self, ts_code: str, trade_date: date) -> float | None:
        if self.price_source == "raw":
            bar = self.get_raw_bar(ts_code, trade_date)
            return bar.open if bar is not None else None
        record = self._adjusted_by_key.get((ts_code, trade_date))
        if record is None or not self._is_valid_adjusted_record(record):
            self._missing_adjusted_count += 1
            return None
        return record.adj_open or record.adj_close

    def get_price_source_status(self) -> dict[str, Any]:
        return {
            "price_source": self.price_source,
            "adjusted_records_count": self._adjusted_records_count,
            "adjusted_invalid_count": self._adjusted_invalid_count,
            "missing_adjusted_count": self._missing_adjusted_count,
        }

    @staticmethod
    def _is_valid_adjusted_record(record: AdjustedDailyBarRecord) -> bool:
        return record.is_valid and record.adj_close is not None and record.adj_close > 0
