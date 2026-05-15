from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from ashare_alpha.data.cache.models import CacheFile, CacheManifest, CacheValidationReport


def save_cache_manifest(manifest: CacheManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache_manifest(path: Path) -> CacheManifest:
    return CacheManifest.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_cache_validation_report(report: CacheValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def cache_file_record(dataset_name: str, base_dir: Path, path: Path) -> CacheFile:
    return CacheFile(
        dataset_name=dataset_name,
        relative_path=str(path.relative_to(base_dir)).replace("\\", "/"),
        rows=count_csv_rows(path),
        sha256=compute_file_sha256(path),
    )


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))
