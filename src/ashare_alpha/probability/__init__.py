from __future__ import annotations

from ashare_alpha.probability.calibration import ScoreBinCalibrator
from ashare_alpha.probability.dataset import ProbabilityDatasetBuilder, split_dataset_by_time
from ashare_alpha.probability.labels import compute_future_return, make_win_label
from ashare_alpha.probability.metrics import evaluate_predictions
from ashare_alpha.probability.models import (
    BinCalibration,
    HorizonModel,
    ProbabilityDatasetRecord,
    ProbabilityMetrics,
    ProbabilityModel,
    ProbabilityPredictionRecord,
    ProbabilityTrainingResult,
)
from ashare_alpha.probability.predictor import ProbabilityPredictor, ProbabilityTrainer
from ashare_alpha.probability.storage import (
    load_probability_model_json,
    save_probability_dataset_csv,
    save_probability_metrics_json,
    save_probability_model_json,
    save_probability_predictions_csv,
    save_probability_summary_md,
)

__all__ = [
    "BinCalibration",
    "HorizonModel",
    "ProbabilityDatasetBuilder",
    "ProbabilityDatasetRecord",
    "ProbabilityMetrics",
    "ProbabilityModel",
    "ProbabilityPredictionRecord",
    "ProbabilityPredictor",
    "ProbabilityTrainer",
    "ProbabilityTrainingResult",
    "ScoreBinCalibrator",
    "compute_future_return",
    "evaluate_predictions",
    "load_probability_model_json",
    "make_win_label",
    "save_probability_dataset_csv",
    "save_probability_metrics_json",
    "save_probability_model_json",
    "save_probability_predictions_csv",
    "save_probability_summary_md",
    "split_dataset_by_time",
]
