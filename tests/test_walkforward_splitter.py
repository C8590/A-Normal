from __future__ import annotations

from datetime import date

from ashare_alpha.walkforward.splitter import generate_walkforward_folds


def test_generate_walkforward_folds_multiple() -> None:
    folds = generate_walkforward_folds(date(2026, 1, 1), date(2026, 2, 15), 14, 7)

    assert len(folds) > 1
    assert folds[0].fold_index == 1


def test_generate_walkforward_folds_end_not_after_end_date() -> None:
    end_date = date(2026, 2, 15)

    folds = generate_walkforward_folds(date(2026, 1, 1), end_date, 14, 7)

    assert all(fold.test_end <= end_date for fold in folds)


def test_generate_walkforward_folds_without_train_window() -> None:
    fold = generate_walkforward_folds(date(2026, 1, 1), date(2026, 1, 31), 14, 14)[0]

    assert fold.train_start is None
    assert fold.train_end is None


def test_generate_walkforward_folds_with_train_window() -> None:
    fold = generate_walkforward_folds(date(2026, 1, 10), date(2026, 2, 10), 10, 10, train_window_days=5)[0]

    assert fold.train_end == date(2026, 1, 9)
    assert fold.train_start == date(2026, 1, 5)


def test_generate_walkforward_folds_empty_interval() -> None:
    folds = generate_walkforward_folds(date(2026, 2, 1), date(2026, 1, 1), 14, 7)

    assert folds == []
