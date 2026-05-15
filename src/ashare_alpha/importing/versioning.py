from __future__ import annotations

import re
from datetime import datetime


_SAFE_SOURCE_PATTERN = re.compile(r"[^a-z0-9_-]+")
_SAFE_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def normalize_source_name(source_name: str) -> str:
    normalized = _SAFE_SOURCE_PATTERN.sub("_", source_name.strip().lower().replace(" ", "_"))
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValueError("source_name 不能为空")
    return normalized


def create_data_version(prefix: str | None = None) -> str:
    timestamp = datetime.now().strftime("v%Y%m%d_%H%M%S")
    if prefix is None or not prefix.strip():
        return timestamp
    safe_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", prefix.strip()).strip("._-")
    if not safe_prefix:
        raise ValueError("data_version prefix 不能为空")
    return f"{safe_prefix}_{timestamp}"


def validate_data_version(data_version: str) -> None:
    if not data_version:
        raise ValueError("data_version 不能为空")
    if ".." in data_version:
        raise ValueError("data_version 不允许包含 '..'")
    if "/" in data_version or "\\" in data_version:
        raise ValueError("data_version 不允许包含路径分隔符")
    if not _SAFE_VERSION_PATTERN.match(data_version):
        raise ValueError("data_version 只能包含字母、数字、下划线、短横线和点")
