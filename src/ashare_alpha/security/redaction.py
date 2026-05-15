from __future__ import annotations

import os
from typing import Any


SENSITIVE_KEYS = {
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_key",
    "refresh_token",
}


def redact_secret(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= 4:
        return "****"
    if len(text) <= 8:
        return f"{text[:1]}****{text[-1:]}"
    return f"{text[:3]}****{text[-3:]}"


def redact_mapping(data: dict) -> dict:
    return _redact_value(data)


def safe_env_status(env_var_name: str) -> dict[str, object]:
    value = os.environ.get(env_var_name)
    return {
        "env_var_name": env_var_name,
        "is_set": value is not None and value != "",
        "redacted_value": redact_secret(value),
    }


def _redact_value(value: Any, key: str | None = None) -> Any:
    if _is_sensitive_key(key):
        if isinstance(value, dict):
            return {item_key: _redact_value(item_value, item_key) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [redact_secret(str(item)) if item is not None else None for item in value]
        return redact_secret(None if value is None else str(value))
    if isinstance(value, dict):
        return {item_key: _redact_value(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _is_sensitive_key(key: str | None) -> bool:
    if key is None:
        return False
    normalized = key.lower()
    return any(item in normalized for item in SENSITIVE_KEYS)
