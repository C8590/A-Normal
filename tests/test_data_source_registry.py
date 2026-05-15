from __future__ import annotations

import pytest

from ashare_alpha.data import DataSourceRegistry, get_default_data_source_registry


def test_list_sources_returns_default_sources() -> None:
    names = {source.name for source in get_default_data_source_registry().list_sources()}

    assert {"local_csv", "tushare_stub", "akshare_stub"} <= names


def test_get_source_missing_fails() -> None:
    with pytest.raises(ValueError, match="Unknown data source"):
        get_default_data_source_registry().get_source("missing")


def test_available_and_stub_sources() -> None:
    registry = get_default_data_source_registry()

    assert [source.name for source in registry.get_available_sources()] == ["local_csv"]
    assert {source.name for source in registry.get_stub_sources()} == {"tushare_stub", "akshare_stub"}


def test_validate_source_exists() -> None:
    registry = get_default_data_source_registry()

    registry.validate_source_exists("local_csv")
    with pytest.raises(ValueError):
        registry.validate_source_exists("missing")


def test_duplicate_registration_fails() -> None:
    source = get_default_data_source_registry().get_source("local_csv")
    registry = DataSourceRegistry()
    registry.register(source)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(source)
