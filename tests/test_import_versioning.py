from __future__ import annotations

import re

import pytest

from ashare_alpha.importing import create_data_version, normalize_source_name, validate_data_version


def test_normalize_source_name() -> None:
    assert normalize_source_name("Local CSV") == "local_csv"


def test_normalize_source_name_replaces_illegal_characters() -> None:
    assert normalize_source_name("Tu$share / Stub") == "tu_share_stub"


def test_normalize_source_name_rejects_empty() -> None:
    with pytest.raises(ValueError, match="source_name"):
        normalize_source_name("   ")


def test_create_data_version_generates_safe_version() -> None:
    value = create_data_version("sample data")

    assert re.match(r"sample_data_v\d{8}_\d{6}", value)
    validate_data_version(value)


def test_validate_data_version_rejects_parent_reference() -> None:
    with pytest.raises(ValueError, match=r"\.\."):
        validate_data_version("sample..v1")


def test_validate_data_version_rejects_path_separator() -> None:
    with pytest.raises(ValueError, match="路径分隔符"):
        validate_data_version("sample/v1")

