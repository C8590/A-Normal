from __future__ import annotations

import math
from statistics import median

from ashare_alpha.walkforward.models import WalkForwardFold


def analyze_walkforward(folds: list[WalkForwardFold]) -> tuple[dict[str, object], list[str], str]:
    successful = [fold for fold in folds if fold.status in {"SUCCESS", "PARTIAL"}]
    returns = [_float_metric(fold, "total_return") for fold in successful]
    returns = [value for value in returns if value is not None]
    drawdowns = [_float_metric(fold, "max_drawdown") for fold in successful]
    drawdowns = [value for value in drawdowns if value is not None]
    trade_counts = [_float_metric(fold, "trade_count") for fold in successful]
    trade_counts = [value for value in trade_counts if value is not None]

    stability: dict[str, object] = {
        "fold_count": len(folds),
        "success_fold_count": len(successful),
    }
    warnings: list[str] = []

    if returns:
        positive_count = sum(1 for value in returns if value > 0)
        mean_return = sum(returns) / len(returns)
        stability.update(
            {
                "positive_return_fold_count": positive_count,
                "positive_return_ratio": positive_count / len(returns),
                "mean_total_return": mean_return,
                "median_total_return": median(returns),
                "std_total_return": _std(returns),
                "min_total_return": min(returns),
                "max_total_return": max(returns),
                "worst_fold_index": _worst_return_fold(successful),
            }
        )
    else:
        stability.update(
            {
                "positive_return_fold_count": 0,
                "positive_return_ratio": None,
                "mean_total_return": None,
                "median_total_return": None,
                "std_total_return": None,
                "min_total_return": None,
                "max_total_return": None,
                "worst_fold_index": None,
            }
        )

    if drawdowns:
        stability["mean_max_drawdown"] = sum(drawdowns) / len(drawdowns)
        stability["worst_max_drawdown"] = min(drawdowns)
    else:
        stability["mean_max_drawdown"] = None
        stability["worst_max_drawdown"] = None

    if len(successful) < 3:
        warnings.append("样本窗口过少，稳定性不足")
    positive_ratio = stability.get("positive_return_ratio")
    if isinstance(positive_ratio, (int, float)) and positive_ratio < 0.5:
        warnings.append("多数窗口未取得正收益")
    mean_total_return = stability.get("mean_total_return")
    std_total_return = stability.get("std_total_return")
    if (
        isinstance(mean_total_return, (int, float))
        and isinstance(std_total_return, (int, float))
        and mean_total_return != 0
        and std_total_return > abs(mean_total_return) * 2
    ):
        warnings.append("收益波动显著高于均值，稳定性较弱")
    worst_max_drawdown = stability.get("worst_max_drawdown")
    if isinstance(worst_max_drawdown, (int, float)) and worst_max_drawdown < -0.10:
        warnings.append("存在较大回撤窗口")
    if trade_counts and all(value == 0 for value in trade_counts):
        warnings.append("INFO: 所有窗口均无交易，说明当前阈值较严格或样例数据未触发 BUY")
    if len(returns) < len(successful) or len(drawdowns) < len(successful):
        warnings.append("INFO: 部分窗口缺少可分析指标")

    summary = _summary_text(successful, returns, warnings)
    return stability, warnings, summary


def _float_metric(fold: WalkForwardFold, name: str) -> float | None:
    value = fold.metrics.get(name)
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _worst_return_fold(folds: list[WalkForwardFold]) -> int | None:
    pairs = [(fold.fold_index, _float_metric(fold, "total_return")) for fold in folds]
    pairs = [(index, value) for index, value in pairs if value is not None]
    if not pairs:
        return None
    return min(pairs, key=lambda item: item[1])[0]


def _summary_text(successful: list[WalkForwardFold], returns: list[float], warnings: list[str]) -> str:
    if not successful:
        return "没有成功完成的 fold，无法评估样本外稳定性。"
    if not returns:
        return "Walk-forward 已完成，但缺少收益指标，稳定性结论有限。"
    if warnings:
        return "Walk-forward 已完成，存在需要关注的稳定性或过拟合风险。"
    return "Walk-forward 已完成，样本外指标未触发主要过拟合风险提示。"
