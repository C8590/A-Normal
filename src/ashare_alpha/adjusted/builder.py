from __future__ import annotations

from collections import defaultdict
from datetime import date

from ashare_alpha.adjusted.formulas import adjust_price, compute_adjustment_ratio, compute_return
from ashare_alpha.adjusted.models import AdjustedBuildSummary, AdjustedDailyBarRecord, AdjustedQualityFlag, AdjustedType
from ashare_alpha.data import DailyBar
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord


class AdjustedDailyBarBuilder:
    def __init__(
        self,
        daily_bars: list[DailyBar],
        adjustment_factors: list[AdjustmentFactorRecord],
        corporate_actions: list[CorporateActionRecord] | None = None,
        adj_type: AdjustedType = "qfq",
    ) -> None:
        if adj_type not in {"qfq", "hfq", "raw"}:
            raise ValueError("adj_type must be one of qfq, hfq, raw")
        self.daily_bars = sorted(daily_bars, key=lambda item: (item.ts_code, item.trade_date))
        self.adjustment_factors = sorted(adjustment_factors, key=lambda item: (item.ts_code, item.adj_type, item.trade_date))
        self.corporate_actions = corporate_actions or []
        self.adj_type: AdjustedType = adj_type
        self._factor_by_key = {
            (item.ts_code, item.trade_date, item.adj_type): item for item in self.adjustment_factors
        }
        self._factors_by_stock_type: dict[tuple[str, str], list[AdjustmentFactorRecord]] = defaultdict(list)
        for factor in self.adjustment_factors:
            self._factors_by_stock_type[(factor.ts_code, factor.adj_type)].append(factor)

    def build_for_range(self, start_date: date, end_date: date) -> tuple[list[AdjustedDailyBarRecord], AdjustedBuildSummary]:
        if start_date > end_date:
            raise ValueError("start_date must be earlier than or equal to end_date")
        bars = [
            bar
            for bar in self.daily_bars
            if bar.is_trading and start_date <= bar.trade_date <= end_date
        ]
        records = self._build_records(bars, start_date=start_date, end_date=end_date)
        summary = self._summary(records, trade_date=None, start_date=start_date, end_date=end_date)
        return records, summary

    def build_for_date(self, trade_date: date) -> tuple[list[AdjustedDailyBarRecord], AdjustedBuildSummary]:
        records, _ = self.build_for_range(trade_date, trade_date)
        summary = self._summary(records, trade_date=trade_date, start_date=None, end_date=None)
        return records, summary

    def _build_records(
        self,
        bars: list[DailyBar],
        start_date: date,
        end_date: date,
    ) -> list[AdjustedDailyBarRecord]:
        bars_by_stock: dict[str, list[DailyBar]] = defaultdict(list)
        for bar in bars:
            bars_by_stock[bar.ts_code].append(bar)

        mismatch_flags = self._corporate_action_flags(start_date, end_date)
        records: list[AdjustedDailyBarRecord] = []
        for ts_code, stock_bars in bars_by_stock.items():
            stock_records: list[AdjustedDailyBarRecord] = []
            base_factor = self._base_factor(ts_code, start_date, end_date)
            previous_raw_close: float | None = None
            previous_adj_close: float | None = None
            for bar in sorted(stock_bars, key=lambda item: item.trade_date):
                record = self._build_one(bar, base_factor, previous_raw_close, previous_adj_close)
                extra_flags = mismatch_flags.get((bar.ts_code, bar.trade_date), [])
                if extra_flags:
                    flags = sorted(set(record.quality_flags + extra_flags))
                    record = record.model_copy(update={"quality_flags": flags, "quality_reason": _quality_reason(flags)})
                stock_records.append(record)
                previous_raw_close = bar.close
                previous_adj_close = record.adj_close
            records.extend(stock_records)
        return sorted(records, key=lambda item: (item.ts_code, item.trade_date))

    def _build_one(
        self,
        bar: DailyBar,
        base_factor: AdjustmentFactorRecord | None,
        previous_raw_close: float | None,
        previous_adj_close: float | None,
    ) -> AdjustedDailyBarRecord:
        flags: list[str] = []
        is_valid = True
        is_adjusted = self.adj_type != "raw"
        adj_factor: float | None = None
        base_adj_factor: float | None = None
        adjustment_ratio: float | None = 1.0 if self.adj_type == "raw" else None

        factor = None
        if self.adj_type != "raw":
            factor = self._factor_for_bar(bar.ts_code, bar.trade_date, flags)
            if factor is None:
                flags.append(AdjustedQualityFlag.MISSING_ADJ_FACTOR.value)
                if self._nearest_previous_factor(bar.ts_code, bar.trade_date) is not None:
                    flags.append(AdjustedQualityFlag.STALE_FACTOR.value)
                is_valid = False
            else:
                adj_factor = factor.adj_factor
                if factor.available_at is None:
                    flags.append(AdjustedQualityFlag.MISSING_FACTOR_AVAILABLE_AT.value)
            if base_factor is None:
                flags.append(AdjustedQualityFlag.MISSING_BASE_FACTOR.value)
                is_valid = False
            else:
                base_adj_factor = base_factor.adj_factor
            if adj_factor is not None and base_adj_factor is not None:
                try:
                    adjustment_ratio = compute_adjustment_ratio(adj_factor, base_adj_factor)
                except ValueError:
                    flags.append(AdjustedQualityFlag.INVALID_ADJ_FACTOR.value)
                    is_valid = False

        adj_open = adj_high = adj_low = adj_close = adj_pre_close = None
        if adjustment_ratio is not None:
            adj_open = adjust_price(bar.open, adjustment_ratio)
            adj_high = adjust_price(bar.high, adjustment_ratio)
            adj_low = adjust_price(bar.low, adjustment_ratio)
            adj_close = adjust_price(bar.close, adjustment_ratio)
            adj_pre_close = adjust_price(bar.pre_close, adjustment_ratio)

        if bar.high < bar.low or bar.low > bar.open or bar.low > bar.close or bar.high < bar.open or bar.high < bar.close:
            flags.append(AdjustedQualityFlag.INVALID_RAW_PRICE.value)
            is_valid = False
        if adj_high is not None and adj_low is not None:
            if adj_high < adj_low or adj_low > (adj_open or 0) or adj_low > (adj_close or 0):
                flags.append(AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value)
                is_valid = False
            if adj_high < (adj_open or 0) or adj_high < (adj_close or 0):
                flags.append(AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value)
                is_valid = False

        flags = sorted(set(flags))
        return AdjustedDailyBarRecord(
            trade_date=bar.trade_date,
            ts_code=bar.ts_code,
            adj_type=self.adj_type,
            raw_open=bar.open,
            raw_high=bar.high,
            raw_low=bar.low,
            raw_close=bar.close,
            raw_pre_close=bar.pre_close,
            volume=bar.volume,
            amount=bar.amount,
            turnover_rate=bar.turnover_rate,
            adj_factor=adj_factor,
            base_adj_factor=base_adj_factor,
            adjustment_ratio=adjustment_ratio,
            adj_open=adj_open,
            adj_high=adj_high,
            adj_low=adj_low,
            adj_close=adj_close,
            adj_pre_close=adj_pre_close,
            raw_return_1d=compute_return(bar.close, previous_raw_close),
            adj_return_1d=compute_return(adj_close, previous_adj_close),
            is_adjusted=is_adjusted,
            is_valid=is_valid,
            quality_flags=flags,
            quality_reason=_quality_reason(flags),
        )

    def _factor_for_bar(
        self,
        ts_code: str,
        trade_date: date,
        flags: list[str],
    ) -> AdjustmentFactorRecord | None:
        factor = self._factor_by_key.get((ts_code, trade_date, self.adj_type))
        if factor is not None:
            return factor
        if self.adj_type != "qfq":
            fallback = self._factor_by_key.get((ts_code, trade_date, "qfq"))
            if fallback is not None:
                flags.append(AdjustedQualityFlag.FALLBACK_ADJ_TYPE.value)
                return fallback
        return None

    def _base_factor(self, ts_code: str, start_date: date, end_date: date) -> AdjustmentFactorRecord | None:
        if self.adj_type == "raw":
            return None
        factors = [
            item
            for item in self._factors_by_stock_type.get((ts_code, self.adj_type), [])
            if start_date <= item.trade_date <= end_date
        ]
        if not factors and self.adj_type != "qfq":
            factors = [
                item
                for item in self._factors_by_stock_type.get((ts_code, "qfq"), [])
                if start_date <= item.trade_date <= end_date
            ]
        if not factors:
            return None
        return factors[-1] if self.adj_type == "qfq" else factors[0]

    def _nearest_previous_factor(self, ts_code: str, trade_date: date) -> AdjustmentFactorRecord | None:
        candidates = [
            item
            for item in self._factors_by_stock_type.get((ts_code, self.adj_type), [])
            if item.trade_date < trade_date
        ]
        if not candidates and self.adj_type != "qfq":
            candidates = [
                item
                for item in self._factors_by_stock_type.get((ts_code, "qfq"), [])
                if item.trade_date < trade_date
            ]
        return candidates[-1] if candidates else None

    def _corporate_action_flags(self, start_date: date, end_date: date) -> dict[tuple[str, date], list[str]]:
        if not self.corporate_actions or self.adj_type == "raw":
            return {}
        factor_changes = self._factor_change_dates(start_date, end_date)
        action_dates: dict[str, list[date]] = defaultdict(list)
        for action in self.corporate_actions:
            effective_date = action.ex_date or action.action_date
            if start_date <= effective_date <= end_date:
                action_dates[action.ts_code].append(effective_date)

        flags: dict[tuple[str, date], list[str]] = defaultdict(list)
        for ts_code, dates in factor_changes.items():
            for changed_date in dates:
                if not _has_nearby_date(action_dates.get(ts_code, []), changed_date):
                    flags[(ts_code, changed_date)].append(
                        AdjustedQualityFlag.FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION.value
                    )
        for ts_code, dates in action_dates.items():
            for action_date in dates:
                if not _has_nearby_date(factor_changes.get(ts_code, []), action_date):
                    flags[(ts_code, action_date)].append(
                        AdjustedQualityFlag.CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE.value
                    )
        return flags

    def _factor_change_dates(self, start_date: date, end_date: date) -> dict[str, list[date]]:
        changes: dict[str, list[date]] = defaultdict(list)
        by_stock: dict[str, list[AdjustmentFactorRecord]] = defaultdict(list)
        for factor in self.adjustment_factors:
            if factor.adj_type == self.adj_type or (self.adj_type != "qfq" and factor.adj_type == "qfq"):
                by_stock[factor.ts_code].append(factor)
        for ts_code, factors in by_stock.items():
            previous: AdjustmentFactorRecord | None = None
            for factor in sorted(factors, key=lambda item: item.trade_date):
                if previous is not None and start_date <= factor.trade_date <= end_date:
                    if abs(factor.adj_factor / previous.adj_factor - 1) > 0.001:
                        changes[ts_code].append(factor.trade_date)
                previous = factor
        return changes

    def _summary(
        self,
        records: list[AdjustedDailyBarRecord],
        trade_date: date | None,
        start_date: date | None,
        end_date: date | None,
    ) -> AdjustedBuildSummary:
        adjusted_records = sum(1 for record in records if record.is_adjusted and record.is_valid)
        invalid_records = sum(1 for record in records if not record.is_valid)
        missing_factor_count = sum(1 for record in records if AdjustedQualityFlag.MISSING_ADJ_FACTOR.value in record.quality_flags)
        stale_factor_count = sum(1 for record in records if AdjustedQualityFlag.STALE_FACTOR.value in record.quality_flags)
        return AdjustedBuildSummary(
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            adj_type=self.adj_type,
            total_records=len(records),
            adjusted_records=adjusted_records,
            invalid_records=invalid_records,
            missing_factor_count=missing_factor_count,
            stale_factor_count=stale_factor_count,
            output_path=None,
            summary=(
                f"adjusted daily bars built: total={len(records)}, adjusted={adjusted_records}, "
                f"invalid={invalid_records}, missing_factor={missing_factor_count}"
            ),
        )


def _has_nearby_date(dates: list[date], target: date) -> bool:
    return any(abs((item - target).days) <= 3 for item in dates)


def _quality_reason(flags: list[str]) -> str:
    if not flags:
        return "复权行情生成正常"
    reason_by_flag = {
        AdjustedQualityFlag.MISSING_ADJ_FACTOR.value: "缺少同日复权因子",
        AdjustedQualityFlag.INVALID_ADJ_FACTOR.value: "复权因子无效",
        AdjustedQualityFlag.FALLBACK_ADJ_TYPE.value: "使用 qfq 复权因子作为回退",
        AdjustedQualityFlag.MISSING_BASE_FACTOR.value: "缺少基准复权因子",
        AdjustedQualityFlag.INVALID_RAW_PRICE.value: "原始价格关系异常",
        AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value: "复权价格关系异常",
        AdjustedQualityFlag.CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE.value: "公司行为附近未发现复权因子变化",
        AdjustedQualityFlag.FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION.value: "复权因子变化附近未发现公司行为",
        AdjustedQualityFlag.STALE_FACTOR.value: "存在历史因子但缺少同日因子",
        AdjustedQualityFlag.MISSING_FACTOR_AVAILABLE_AT.value: "复权因子缺少 available_at",
    }
    return "；".join(reason_by_flag.get(flag, flag) for flag in flags)
