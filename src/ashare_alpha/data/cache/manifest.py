from __future__ import annotations

from ashare_alpha.importing.versioning import create_data_version, normalize_source_name, validate_data_version


def create_cache_version(prefix: str | None = None) -> str:
    return create_data_version(prefix or "cache")


def build_cache_id(source_name: str, cache_version: str) -> str:
    normalized_source = normalize_source_name(source_name)
    validate_data_version(cache_version)
    return f"{normalized_source}_{cache_version}"
