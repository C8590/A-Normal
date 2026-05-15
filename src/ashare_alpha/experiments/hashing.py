from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


HASH_EXTENSIONS = {".yaml", ".yml", ".json"}
SKIPPED_PARTS = {"__pycache__", "outputs", ".pytest_cache", ".ruff_cache"}


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_config_dir(config_dir: Path) -> str:
    base = Path(config_dir)
    digest = hashlib.sha256()
    files = sorted(path for path in base.rglob("*") if _is_hashable_config_file(path))
    for path in files:
        relative = path.relative_to(base).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hash_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def create_experiment_id(
    command: str,
    command_args: dict[str, Any],
    config_hash: str | None,
    data_version: str | None,
    created_at: datetime | None = None,
) -> str:
    timestamp = created_at or datetime.now()
    payload = {
        "command": command,
        "command_args": _jsonable(command_args),
        "config_hash": config_hash,
        "data_version": data_version,
        "created_at": timestamp.isoformat(),
    }
    short_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"exp_{timestamp.strftime('%Y%m%d_%H%M%S')}_{short_hash}"


def _is_hashable_config_file(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in HASH_EXTENSIONS:
        return False
    if any(part in SKIPPED_PARTS for part in path.parts):
        return False
    name = path.name.lower()
    return not (name.startswith("~") or name.endswith(".tmp") or name.endswith(".bak"))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
