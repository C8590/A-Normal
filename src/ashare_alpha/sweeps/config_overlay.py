from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from ashare_alpha.config import load_project_config


_CONFIG_SUFFIXES = {".yaml", ".yml", ".json"}
_SKIP_DIRS = {"__pycache__", "outputs", "data"}
_SENSITIVE_KEYS = ("token", "api_key", "secret", "password")


def copy_config_dir(base_config_dir: Path, target_config_dir: Path) -> None:
    base = Path(base_config_dir)
    target = Path(target_config_dir)
    if not base.exists() or not base.is_dir():
        raise ValueError(f"base_config_dir does not exist or is not a directory: {base}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.suffix.lower() not in _CONFIG_SUFFIXES:
            continue
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def apply_config_overrides(config_dir: Path, overrides: dict[str, object]) -> list[str]:
    base = Path(config_dir)
    changes: list[str] = []
    if not overrides:
        load_project_config(base)
        return changes

    for file_name, file_overrides in overrides.items():
        if not isinstance(file_overrides, dict):
            raise ValueError(f"Overrides for {file_name} must be a mapping")
        path = _resolve_config_file(base, file_name)
        payload = _load_mapping(path)
        for dot_path, value in file_overrides.items():
            if not isinstance(dot_path, str) or not dot_path.strip():
                raise ValueError(f"Override path in {file_name} must be a non-empty string")
            _validate_safe_override(path.name, dot_path, value)
            old_value = _set_existing_dot_path(payload, dot_path, value)
            changes.append(f"{path.name}: {dot_path} {_format_value(old_value)} -> {_format_value(value)}")
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    load_project_config(base)
    return changes


def _resolve_config_file(config_dir: Path, file_name: str) -> Path:
    rel = Path(file_name)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Config override file must stay inside config_dir: {file_name}")
    path = config_dir / rel
    try:
        path.resolve().relative_to(config_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"Config override file must stay inside config_dir: {file_name}") from exc
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"Only existing YAML config files can be overridden: {file_name}")
    if not path.exists() or not path.is_file():
        raise ValueError(f"Config file does not exist: {file_name}")
    return path


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def _set_existing_dot_path(payload: dict[str, Any], dot_path: str, value: Any) -> Any:
    parts = dot_path.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise ValueError(f"Config dot path does not exist: {dot_path}")
        cursor = cursor[part]
    leaf = parts[-1]
    if not isinstance(cursor, dict) or leaf not in cursor:
        raise ValueError(f"Config dot path does not exist: {dot_path}")
    old_value = cursor[leaf]
    cursor[leaf] = value
    return old_value


def _validate_safe_override(file_name: str, dot_path: str, value: Any) -> None:
    normalized_file = file_name.lower()
    normalized_path = dot_path.lower()
    if normalized_file == "security.yaml" and normalized_path in {
        "allow_network",
        "allow_broker_connections",
        "allow_live_trading",
    } and value is True:
        raise ValueError(f"Sweep cannot enable {file_name}: {dot_path}")
    if normalized_file == "security.yaml" and normalized_path == "offline_mode" and value is False:
        raise ValueError("Sweep cannot set security.yaml: offline_mode to false")
    if any(key in normalized_path for key in _SENSITIVE_KEYS) and not _is_allowed_secret_value(value):
        raise ValueError(f"Sweep cannot write plaintext secret-like override: {file_name}: {dot_path}")


def _is_allowed_secret_value(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.startswith("ASHARE_ALPHA_"))


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    return repr(value)
