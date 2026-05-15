from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_alpha.data import DataValidationReport
from ashare_alpha.importing.models import ImportManifest


def save_import_manifest(manifest: ImportManifest, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_import_manifest(path: Path) -> ImportManifest:
    if not path.exists():
        raise ValueError(f"import_manifest.json not found: {path}")
    return ImportManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_validation_report(report: DataValidationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
