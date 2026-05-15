from __future__ import annotations

from datetime import date, timedelta

from ashare_alpha.walkforward.models import WalkForwardFold


def generate_walkforward_folds(
    start_date: date,
    end_date: date,
    test_window_days: int,
    step_days: int,
    train_window_days: int | None = None,
) -> list[WalkForwardFold]:
    if start_date >= end_date or test_window_days <= 0 or step_days <= 0:
        return []

    folds: list[WalkForwardFold] = []
    test_start = start_date
    fold_index = 1
    while test_start <= end_date:
        test_end = test_start + timedelta(days=test_window_days - 1)
        if test_end > end_date:
            break
        train_start = None
        train_end = None
        if train_window_days is not None:
            train_end = test_start - timedelta(days=1)
            train_start = train_end - timedelta(days=train_window_days - 1)
        folds.append(
            WalkForwardFold(
                fold_index=fold_index,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        fold_index += 1
        test_start += timedelta(days=step_days)
    return folds
