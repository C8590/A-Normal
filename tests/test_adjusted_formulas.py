from __future__ import annotations

import pytest

from ashare_alpha.adjusted.formulas import adjust_price, compute_adjustment_ratio, compute_return


def test_compute_adjustment_ratio() -> None:
    assert compute_adjustment_ratio(1.02, 1.0) == pytest.approx(1.02)


def test_compute_adjustment_ratio_rejects_nonpositive_values() -> None:
    with pytest.raises(ValueError):
        compute_adjustment_ratio(0, 1.0)


def test_adjust_price_and_return() -> None:
    assert adjust_price(10, 1.02) == pytest.approx(10.2)
    assert compute_return(10.2, 10.0) == pytest.approx(0.02)
    assert compute_return(10.2, 0) is None
