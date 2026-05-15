from __future__ import annotations

import math
from datetime import date

from ashare_alpha.backtest.engine import get_trading_dates
from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.probability.labels import compute_future_return, make_win_label
from ashare_alpha.probability.models import ProbabilityDatasetRecord, set_horizon_value
from ashare_alpha.signals import SignalDailyRecord, SignalGenerator
from ashare_alpha.universe import UniverseBuilder


class ProbabilityDatasetBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self.daily_bars = daily_bars
        self.financial_summary = financial_summary
        self.announcement_events = announcement_events

    def build_dataset(self, start_date: date, end_date: date) -> list[ProbabilityDatasetRecord]:
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        records: list[ProbabilityDatasetRecord] = []
        for trade_date in get_trading_dates(self.daily_bars, start_date, end_date):
            records.extend(self._build_for_date(trade_date))
        return sorted(records, key=lambda record: (record.trade_date, record.ts_code))

    def _build_for_date(self, trade_date: date) -> list[ProbabilityDatasetRecord]:
        universe_records = UniverseBuilder(
            self.config,
            self.stock_master,
            self.daily_bars,
            self.financial_summary,
            self.announcement_events,
        ).build_for_date(trade_date)
        factor_records = FactorBuilder(self.config, self.daily_bars, self.stock_master).build_for_date(trade_date)
        event_records = EventFeatureBuilder(self.config, self.announcement_events, self.stock_master).build_for_date(
            trade_date
        )
        signals = SignalGenerator(
            self.config,
            self.stock_master,
            self.financial_summary,
            universe_records,
            factor_records,
            event_records,
        ).generate_for_date(trade_date)
        factor_by_code = {record.ts_code: record for record in factor_records}
        output = []
        for signal in signals:
            factor = factor_by_code.get(signal.ts_code)
            if self.config.probability.include_only_universe_allowed and not signal.universe_allowed:
                continue
            if self.config.probability.include_only_computable_factors and (factor is None or not factor.is_computable):
                continue
            output.append(self._record_from_signal(signal, factor, trade_date))
        return output

    def _record_from_signal(self, signal: SignalDailyRecord, factor, trade_date: date) -> ProbabilityDatasetRecord:
        payload = {
            "trade_date": trade_date,
            "ts_code": signal.ts_code,
            "symbol": signal.symbol,
            "name": signal.name,
            "industry": signal.industry,
            "stock_score": signal.stock_score,
            "raw_score": signal.raw_score,
            "risk_penalty_score": signal.risk_penalty_score,
            "market_regime_score": signal.market_regime_score,
            "industry_strength_score": signal.industry_strength_score,
            "trend_momentum_score": signal.trend_momentum_score,
            "fundamental_quality_score": signal.fundamental_quality_score,
            "liquidity_score": signal.liquidity_score,
            "event_component_score": signal.event_component_score,
            "volatility_control_score": signal.volatility_control_score,
            "event_score": signal.event_score,
            "event_risk_score": signal.event_risk_score,
            "universe_allowed": signal.universe_allowed,
            "signal": signal.signal,
            "risk_level": signal.risk_level,
            "latest_close": factor.latest_close if factor is not None and factor.latest_close is not None else 0,
        }
        missing_reasons = []
        if payload["latest_close"] <= 0:
            missing_reasons.append("当日收盘价缺失，无法训练概率标签")
            payload["latest_close"] = 0.000001
        for horizon in self.config.probability.horizons:
            future_return = compute_future_return(self.daily_bars, signal.ts_code, trade_date, horizon)
            set_horizon_value(payload, "future_return", horizon, future_return)
            set_horizon_value(payload, "y_win", horizon, make_win_label(future_return, self.config.probability.win_return_threshold))
        has_label = any(payload.get(f"y_win_{horizon}d") is not None for horizon in self.config.probability.horizons)
        if not has_label:
            missing_reasons.append("未来交易日不足，缺少可用训练标签")
        is_trainable = payload["latest_close"] > 0 and has_label
        return ProbabilityDatasetRecord(
            **payload,
            is_trainable=is_trainable,
            missing_reasons=missing_reasons,
        )


def split_dataset_by_time(
    records: list[ProbabilityDatasetRecord],
    train_test_split_ratio: float,
    max_horizon: int,
    purge_gap: bool,
) -> tuple[list[ProbabilityDatasetRecord], list[ProbabilityDatasetRecord]]:
    if not records:
        return [], []
    unique_dates = sorted({record.trade_date for record in records})
    if len(unique_dates) < 2:
        return [record for record in records if record.is_trainable], []
    split_index = math.floor(len(unique_dates) * train_test_split_ratio)
    split_index = min(max(split_index, 1), len(unique_dates))
    test_start_date = unique_dates[split_index] if split_index < len(unique_dates) else None
    if test_start_date is None:
        return [record for record in records if record.is_trainable], []

    train_dates = [trade_date for trade_date in unique_dates if trade_date < test_start_date]
    if purge_gap and max_horizon > 0:
        train_dates = train_dates[: max(0, len(train_dates) - max_horizon)]
    train_date_set = set(train_dates)
    train_records = [record for record in records if record.trade_date in train_date_set and record.is_trainable]
    test_records = [record for record in records if record.trade_date >= test_start_date and record.is_trainable]
    return train_records, test_records
