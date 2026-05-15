from __future__ import annotations

from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.probability.calibration import ScoreBinCalibrator
from ashare_alpha.probability.dataset import ProbabilityDatasetBuilder, split_dataset_by_time
from ashare_alpha.probability.metrics import evaluate_predictions
from ashare_alpha.probability.models import (
    ProbabilityDatasetRecord,
    ProbabilityModel,
    ProbabilityPredictionRecord,
    ProbabilityTrainingResult,
)
from ashare_alpha.signals import SignalGenerator
from ashare_alpha.universe import UniverseBuilder


class ProbabilityTrainer:
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
        self.last_dataset: list[ProbabilityDatasetRecord] = []
        self.last_test_predictions: list[ProbabilityPredictionRecord] = []

    def train(self, start_date: date, end_date: date) -> ProbabilityTrainingResult:
        dataset = ProbabilityDatasetBuilder(
            self.config,
            self.stock_master,
            self.daily_bars,
            self.financial_summary,
            self.announcement_events,
        ).build_dataset(start_date, end_date)
        train_records, test_records = split_dataset_by_time(
            dataset,
            self.config.probability.train_test_split_ratio,
            max(self.config.probability.horizons),
            self.config.probability.purge_gap,
        )
        calibrator = ScoreBinCalibrator(self.config)
        model = calibrator.fit(train_records)
        train_dates = sorted({record.trade_date for record in train_records})
        test_dates = sorted({record.trade_date for record in test_records})
        if train_dates:
            model = model.model_copy(update={"train_start_date": train_dates[0], "train_end_date": train_dates[-1]})
        if test_dates:
            model = model.model_copy(update={"test_start_date": test_dates[0], "test_end_date": test_dates[-1]})
        test_predictions = [calibrator.predict_one(record, model) for record in test_records]
        metrics = evaluate_predictions(
            test_records,
            test_predictions,
            list(self.config.probability.horizons),
            self.config.probability.prediction_threshold,
        )
        self.last_dataset = dataset
        self.last_test_predictions = test_predictions
        return ProbabilityTrainingResult(
            model=model,
            metrics=metrics,
            train_rows=len(train_records),
            test_rows=len(test_records),
            dataset_rows=len(dataset),
            skipped_rows=sum(1 for record in dataset if not record.is_trainable),
            summary=_training_summary(model, len(dataset), len(train_records), len(test_records)),
        )


class ProbabilityPredictor:
    def __init__(
        self,
        config: ProjectConfig,
        model: ProbabilityModel,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
    ) -> None:
        self.config = config
        self.model = model
        self.stock_master = stock_master
        self.daily_bars = daily_bars
        self.financial_summary = financial_summary
        self.announcement_events = announcement_events

    def predict_for_date(self, trade_date: date) -> list[ProbabilityPredictionRecord]:
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
        predictions = []
        calibrator = ScoreBinCalibrator(self.config)
        for signal in sorted(signals, key=lambda item: item.ts_code):
            factor = factor_by_code.get(signal.ts_code)
            missing_reasons = []
            if self.config.probability.include_only_universe_allowed and not signal.universe_allowed:
                missing_reasons.append("股票池过滤未通过，暂不输出概率")
            if self.config.probability.include_only_computable_factors and (factor is None or not factor.is_computable):
                missing_reasons.append("行情因子不可计算，暂不输出概率")
            latest_close = factor.latest_close if factor is not None else None
            if latest_close is None or latest_close <= 0:
                missing_reasons.append("当日收盘价缺失，暂不输出概率")
            if missing_reasons:
                predictions.append(_unpredictable_from_signal(signal, latest_close, missing_reasons))
                continue
            feature_record = _feature_record_from_signal(signal, latest_close)
            predictions.append(calibrator.predict_one(feature_record, self.model))
        return predictions


def _feature_record_from_signal(signal, latest_close: float) -> ProbabilityDatasetRecord:
    return ProbabilityDatasetRecord(
        trade_date=signal.trade_date,
        ts_code=signal.ts_code,
        symbol=signal.symbol,
        name=signal.name,
        industry=signal.industry,
        stock_score=signal.stock_score,
        raw_score=signal.raw_score,
        risk_penalty_score=signal.risk_penalty_score,
        market_regime_score=signal.market_regime_score,
        industry_strength_score=signal.industry_strength_score,
        trend_momentum_score=signal.trend_momentum_score,
        fundamental_quality_score=signal.fundamental_quality_score,
        liquidity_score=signal.liquidity_score,
        event_component_score=signal.event_component_score,
        volatility_control_score=signal.volatility_control_score,
        event_score=signal.event_score,
        event_risk_score=signal.event_risk_score,
        universe_allowed=signal.universe_allowed,
        signal=signal.signal,
        risk_level=signal.risk_level,
        latest_close=latest_close,
        is_trainable=True,
        missing_reasons=[],
    )


def _unpredictable_from_signal(signal, latest_close: float | None, missing_reasons: list[str]) -> ProbabilityPredictionRecord:
    return ProbabilityPredictionRecord(
        trade_date=signal.trade_date,
        ts_code=signal.ts_code,
        symbol=signal.symbol,
        name=signal.name,
        industry=signal.industry,
        is_predictable=False,
        missing_reasons=missing_reasons,
        stock_score=signal.stock_score,
        risk_level=signal.risk_level,
        signal=signal.signal,
        latest_close=latest_close if latest_close and latest_close > 0 else None,
        confidence_level="low",
        reason="；".join(missing_reasons),
    )


def _training_summary(model: ProbabilityModel, dataset_rows: int, train_rows: int, test_rows: int) -> str:
    untrained = [item.horizon for item in model.horizon_models.values() if not item.trained]
    base = f"概率数据集 {dataset_rows} 行，训练集 {train_rows} 行，测试集 {test_rows} 行。"
    if untrained:
        return base + f"部分周期样本数量不足，未充分训练：{', '.join(str(item) for item in untrained)}。"
    return base + "所有配置周期均已完成分箱胜率校准训练。"
