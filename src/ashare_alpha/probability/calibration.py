from __future__ import annotations

from datetime import datetime

from ashare_alpha.config import ProjectConfig
from ashare_alpha.probability.models import (
    FEATURE_COLUMNS,
    BinCalibration,
    HorizonModel,
    ProbabilityDatasetRecord,
    ProbabilityModel,
    ProbabilityPredictionRecord,
    get_future_return,
    get_win_label,
    set_horizon_value,
)


class ScoreBinCalibrator:
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config

    def fit(self, train_records: list[ProbabilityDatasetRecord]) -> ProbabilityModel:
        train_dates = sorted({record.trade_date for record in train_records})
        horizon_models = {
            str(horizon): self._fit_horizon(train_records, horizon) for horizon in self.config.probability.horizons
        }
        fallback_date = train_dates[0] if train_dates else datetime.now().date()
        return ProbabilityModel(
            trained_at=datetime.now(),
            train_start_date=train_dates[0] if train_dates else fallback_date,
            train_end_date=train_dates[-1] if train_dates else fallback_date,
            test_start_date=None,
            test_end_date=None,
            horizons=list(self.config.probability.horizons),
            score_field=self.config.probability.score_field,
            n_bins=self.config.probability.n_bins,
            prior_strength=self.config.probability.prior_strength,
            horizon_models=horizon_models,
            feature_columns=FEATURE_COLUMNS,
        )

    def predict_one(self, record: ProbabilityDatasetRecord, model: ProbabilityModel) -> ProbabilityPredictionRecord:
        score = getattr(record, model.score_field, None)
        missing_reasons = []
        if score is None:
            missing_reasons.append(f"{model.score_field} 缺失，无法预测")
        if record.latest_close <= 0:
            missing_reasons.append("当日收盘价缺失，无法预测")
        if missing_reasons:
            return _unpredictable_from_record(record, missing_reasons)

        payload = _base_prediction_payload(record)
        bin_sample_counts = []
        trained_horizon_count = 0
        for horizon in model.horizons:
            horizon_model = model.horizon_models.get(str(horizon))
            if horizon_model is None or not horizon_model.trained or not horizon_model.bins:
                continue
            trained_horizon_count += 1
            selected_bin = _find_bin(float(score), horizon_model.bins)
            set_horizon_value(payload, "p_win", horizon, selected_bin.smoothed_win_probability)
            set_horizon_value(payload, "expected_return", horizon, selected_bin.smoothed_expected_return)
            set_horizon_value(payload, "bin_index", horizon, selected_bin.bin_index)
            set_horizon_value(payload, "bin_sample_count", horizon, selected_bin.sample_count)
            bin_sample_counts.append(selected_bin.sample_count)

        if trained_horizon_count == 0:
            return _unpredictable_from_record(record, ["模型样本不足，无法预测"])

        min_bin_samples = self.config.probability.min_bin_samples
        if bin_sample_counts and all(count >= min_bin_samples * 2 for count in bin_sample_counts):
            confidence = "high"
            reason = "基于 stock_score 分箱校准得到概率，分箱样本量较充足。"
        elif any(count >= min_bin_samples for count in bin_sample_counts):
            confidence = "medium"
            reason = "基于 stock_score 分箱校准得到概率，分箱样本量中等。"
        else:
            confidence = "low"
            reason = "基于 stock_score 分箱校准得到概率；样本量较低，置信度低。"

        return ProbabilityPredictionRecord(
            **payload,
            is_predictable=True,
            missing_reasons=[],
            confidence_level=confidence,
            reason=reason,
        )

    def _fit_horizon(self, train_records: list[ProbabilityDatasetRecord], horizon: int) -> HorizonModel:
        samples = [
            record
            for record in train_records
            if get_win_label(record, horizon) is not None and get_future_return(record, horizon) is not None
        ]
        if len(samples) < self.config.probability.min_train_samples:
            return HorizonModel(
                horizon=horizon,
                score_field=self.config.probability.score_field,
                global_sample_count=len(samples),
                global_win_rate=_mean([get_win_label(record, horizon) or 0 for record in samples]),
                global_mean_return=_mean([get_future_return(record, horizon) or 0.0 for record in samples]),
                bins=[],
                trained=False,
                reason="样本数量不足，暂不训练该周期模型",
            )

        labels = [get_win_label(record, horizon) or 0 for record in samples]
        returns = [get_future_return(record, horizon) or 0.0 for record in samples]
        global_win_rate = _mean(labels)
        global_mean_return = _mean(returns)
        bins = self._fit_bins(samples, horizon, global_win_rate, global_mean_return)
        return HorizonModel(
            horizon=horizon,
            score_field=self.config.probability.score_field,
            global_sample_count=len(samples),
            global_win_rate=global_win_rate,
            global_mean_return=global_mean_return,
            bins=bins,
            trained=True,
            reason=None,
        )

    def _fit_bins(
        self,
        samples: list[ProbabilityDatasetRecord],
        horizon: int,
        global_win_rate: float,
        global_mean_return: float,
    ) -> list[BinCalibration]:
        score_field = self.config.probability.score_field
        sorted_scores = sorted(float(getattr(record, score_field)) for record in samples)
        edges = _quantile_edges(sorted_scores, self.config.probability.n_bins)
        bins: list[BinCalibration] = []
        for index, (lower, upper) in enumerate(zip(edges, edges[1:])):
            bin_samples = [
                record for record in samples if _score_in_bin(float(getattr(record, score_field)), lower, upper, index, len(edges) - 2)
            ]
            labels = [get_win_label(record, horizon) or 0 for record in bin_samples]
            returns = [get_future_return(record, horizon) or 0.0 for record in bin_samples]
            sample_count = len(bin_samples)
            win_count = sum(labels)
            raw_win_rate = win_count / sample_count if sample_count else 0.0
            mean_return = sum(returns) / sample_count if sample_count else 0.0
            prior = self.config.probability.prior_strength
            smoothed_probability = (
                (win_count + prior * global_win_rate) / (sample_count + prior)
                if sample_count + prior > 0
                else global_win_rate
            )
            return_sum = sum(returns)
            smoothed_return = (
                (return_sum + prior * global_mean_return) / (sample_count + prior)
                if sample_count + prior > 0
                else global_mean_return
            )
            bins.append(
                BinCalibration(
                    bin_index=index,
                    lower_bound=lower,
                    upper_bound=upper,
                    sample_count=sample_count,
                    win_count=win_count,
                    raw_win_rate=raw_win_rate,
                    smoothed_win_probability=smoothed_probability,
                    mean_future_return=mean_return,
                    smoothed_expected_return=smoothed_return,
                )
            )
        return bins


def _base_prediction_payload(record: ProbabilityDatasetRecord) -> dict:
    return {
        "trade_date": record.trade_date,
        "ts_code": record.ts_code,
        "symbol": record.symbol,
        "name": record.name,
        "industry": record.industry,
        "stock_score": record.stock_score,
        "risk_level": record.risk_level,
        "signal": record.signal,
        "latest_close": record.latest_close,
    }


def _unpredictable_from_record(record: ProbabilityDatasetRecord, missing_reasons: list[str]) -> ProbabilityPredictionRecord:
    return ProbabilityPredictionRecord(
        **_base_prediction_payload(record),
        is_predictable=False,
        missing_reasons=missing_reasons,
        confidence_level="low",
        reason="；".join(missing_reasons),
    )


def _quantile_edges(sorted_scores: list[float], n_bins: int) -> list[float]:
    if not sorted_scores:
        return [0.0, 100.0]
    if sorted_scores[0] == sorted_scores[-1]:
        return [sorted_scores[0], sorted_scores[-1]]
    raw_edges = []
    last_index = len(sorted_scores) - 1
    for index in range(n_bins + 1):
        position = round(last_index * index / n_bins)
        raw_edges.append(sorted_scores[position])
    edges = []
    for edge in raw_edges:
        if not edges or edge > edges[-1]:
            edges.append(edge)
    if len(edges) < 2:
        return [sorted_scores[0], sorted_scores[-1]]
    return edges


def _score_in_bin(score: float, lower: float, upper: float, index: int, last_index: int) -> bool:
    if index == 0 and score < lower:
        return False
    if index == last_index:
        return lower <= score <= upper
    return lower <= score < upper


def _find_bin(score: float, bins: list[BinCalibration]) -> BinCalibration:
    if len(bins) == 1:
        return bins[0]
    for index, item in enumerate(bins):
        if _score_in_bin(score, item.lower_bound, item.upper_bound, index, len(bins) - 1):
            return item
    if score < bins[0].lower_bound:
        return bins[0]
    return bins[-1]


def _mean(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))
