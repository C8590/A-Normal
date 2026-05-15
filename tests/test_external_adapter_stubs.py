from __future__ import annotations

import sys

import pytest

from ashare_alpha.data import AkshareAdapterStub, ExternalDataAdapterStub, TushareAdapterStub


@pytest.mark.parametrize("adapter", [ExternalDataAdapterStub(), TushareAdapterStub(), AkshareAdapterStub()])
def test_stub_load_methods_raise_not_implemented(adapter) -> None:
    methods = [
        adapter.load_stock_master,
        adapter.load_daily_bars,
        adapter.load_financial_summary,
        adapter.load_announcement_events,
        adapter.validate_all,
    ]

    for method in methods:
        with pytest.raises(NotImplementedError, match="stub"):
            method()


def test_stubs_do_not_import_external_data_libraries() -> None:
    assert "tushare" not in sys.modules
    assert "akshare" not in sys.modules
