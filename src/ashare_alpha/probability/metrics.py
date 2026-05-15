from __future__ import annotations

from ashare_alpha.probability.models import (
    ProbabilityDatasetRecord,
    ProbabilityMetrics,
    ProbabilityPredictionRecord,
    get_future_return,
    get_win_label,
)


def evaluate_predictions(
    records: list[ProbabilityDatasetRecord],
    predictions: list[ProbabilityPredictionRecord],
    horizons: list[int],
    prediction_threshold: float,
) -> list[ProbabilityMetrics]:
    prediction_by_key = {(item.trade_date, item.ts_code): item for item in predictions}
    metrics = []
    for horizon in horizons:
        pairs = []
        returns = []
        for record in records:
            prediction = prediction_by_key.get((record.trade_date, record.ts_code))
            label = get_win_label(record, horizon)
            probability = getattr(prediction, f"p_win_{horizon}d", None) if prediction is not None else None
            future_return = get_future_return(record, horizon)
            if label is None or probability is None or future_return is None:
                continue
            pairs.append((int(label), float(probability)))
            returns.append(float(future_return))
        metrics.append(_metrics_for_horizon(horizon, pairs, returns, prediction_threshold))
    return metrics


def _metrics_for_horizon(
    horizon: int,
    pairs: list[tuple[int, float]],
    returns: list[float],
    prediction_threshold: float,
) -> ProbabilityMetrics:
    sample_count = len(pairs)
    if sample_count == 0:
        return ProbabilityMetrics(
            horizon=horizon,
            sample_count=0,
            positive_count=0,
            accuracy=None,
            precision=None,
            recall=None,
            auc=None,
            brier_score=None,
            average_predicted_probability=None,
            actual_win_rate=None,
            average_future_return=None,
        )

    labels = [label for label, _ in pairs]
    probabilities = [probability for _, probability in pairs]
    predicted_labels = [1 if probability >= prediction_threshold else 0 for probability in probabilities]
    positive_count = sum(labels)
    true_positive = sum(1 for y, pred in zip(labels, predicted_labels) if y == 1 and pred == 1)
    false_positive = sum(1 for y, pred in zip(labels, predicted_labels) if y == 0 and pred == 1)
    false_negative = sum(1 for y, pred in zip(labels, predicted_labels) if y == 1 and pred == 0)
    accuracy = sum(1 for y, pred in zip(labels, predicted_labels) if y == pred) / sample_count
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive > 0 else None
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative > 0 else None
    brier_score = sum((probability - label) ** 2 for label, probability in pairs) / sample_count

    return ProbabilityMetrics(
        horizon=horizon,
        sample_count=sample_count,
        positive_count=positive_count,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        auc=_auc(labels, probabilities),
        brier_score=brier_score,
        average_predicted_probability=sum(probabilities) / sample_count,
        actual_win_rate=positive_count / sample_count,
        average_future_return=sum(returns) / len(returns),
    )


def _auc(labels: list[int], probabilities: list[float]) -> float | None:
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if positive_count == 0 or negative_count == 0:
        return None

    ranked = sorted(enumerate(probabilities), key=lambda item: item[1])
    ranks = [0.0] * len(probabilities)
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][1] == ranked[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2
        for rank_index in range(index, end):
            original_index = ranked[rank_index][0]
            ranks[original_index] = average_rank
        index = end

    positive_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    return (positive_rank_sum - positive_count * (positive_count + 1) / 2) / (positive_count * negative_count)
