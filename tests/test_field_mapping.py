from __future__ import annotations

import pytest

from ashare_alpha.data import DAILY_BAR_REQUIRED_FIELDS, FieldMapping


def test_field_mapping_applies_source_to_internal_fields() -> None:
    mapping = FieldMapping(
        source_to_internal={
            "code": "ts_code",
            "date": "trade_date",
            "vol": "volume",
        },
        required_internal_fields=("ts_code", "trade_date", "volume"),
    )
    row = {"code": "600001.SH", "date": "2026-03-20", "vol": 100}

    assert mapping.apply_mapping(row) == {
        "ts_code": "600001.SH",
        "trade_date": "2026-03-20",
        "volume": 100,
    }


def test_field_mapping_missing_required_field_fails_clearly() -> None:
    mapping = FieldMapping(
        source_to_internal={"code": "ts_code"},
        required_internal_fields=("ts_code", "trade_date"),
    )

    with pytest.raises(ValueError, match="trade_date"):
        mapping.validate_required_fields({"code": "600001.SH"})


def test_daily_bar_required_fields_include_core_ohlcv() -> None:
    assert {"ts_code", "trade_date", "open", "high", "low", "close", "volume"} <= set(DAILY_BAR_REQUIRED_FIELDS)
