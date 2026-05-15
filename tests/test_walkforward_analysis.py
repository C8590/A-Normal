from __future__ import annotations

from datetime import date

from ashare_alpha.walkforward.analysis import analyze_walkforward
from ashare_alpha.walkforward.models import WalkForwardFold


def test_analyze_walkforward_positive_ratio_and_return_stats() -> None:
    folds = [
        _fold(1, total_return=0.10, max_drawdown=-0.02, trade_count=1),
        _fold(2, total_return=-0.05, max_drawdown=-0.04, trade_count=1),
        _fold(3, total_return=0.00, max_drawdown=-0.01, trade_count=1),
    ]

    metrics, warnings, summary = analyze_walkforward(folds)

    assert metrics["positive_return_ratio"] == 1 / 3
    assert metrics["mean_total_return"] == (0.10 - 0.05 + 0.00) / 3
    assert metrics["min_total_return"] == -0.05
    assert metrics["max_total_return"] == 0.10
    assert metrics["worst_fold_index"] == 2
    assert "多数窗口未取得正收益" in warnings
    assert "Walk-forward" in summary


def test_analyze_walkforward_worst_drawdown() -> None:
    metrics, _, _ = analyze_walkforward(
        [
            _fold(1, total_return=0.01, max_drawdown=-0.02, trade_count=1),
            _fold(2, total_return=0.02, max_drawdown=-0.12, trade_count=1),
        ]
    )

    assert metrics["worst_max_drawdown"] == -0.12
    assert metrics["mean_max_drawdown"] == (-0.02 - 0.12) / 2


def test_analyze_walkforward_warns_all_no_trade() -> None:
    _, warnings, _ = analyze_walkforward(
        [
            _fold(1, total_return=0.0, max_drawdown=0.0, trade_count=0),
            _fold(2, total_return=0.0, max_drawdown=0.0, trade_count=0),
            _fold(3, total_return=0.0, max_drawdown=0.0, trade_count=0),
        ]
    )

    assert any("所有窗口均无交易" in warning for warning in warnings)


def test_analyze_walkforward_warns_few_folds() -> None:
    _, warnings, _ = analyze_walkforward([_fold(1, total_return=0.1, max_drawdown=0.0, trade_count=1)])

    assert "样本窗口过少，稳定性不足" in warnings


def test_analyze_walkforward_no_success_does_not_crash() -> None:
    metrics, warnings, summary = analyze_walkforward(
        [
            WalkForwardFold(
                fold_index=1,
                test_start=date(2026, 1, 1),
                test_end=date(2026, 1, 10),
                status="FAILED",
                error_message="boom",
            )
        ]
    )

    assert metrics["success_fold_count"] == 0
    assert "样本窗口过少" in warnings[0]
    assert "没有成功完成" in summary


def _fold(fold_index: int, **metrics) -> WalkForwardFold:
    return WalkForwardFold(
        fold_index=fold_index,
        test_start=date(2026, 1, fold_index),
        test_end=date(2026, 1, fold_index + 5),
        status="SUCCESS",
        metrics=metrics,
    )
