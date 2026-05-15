from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data.adapters.local_csv import LocalCsvAdapter
from ashare_alpha.data.cache.manifest import build_cache_id, create_cache_version
from ashare_alpha.data.cache.models import CacheManifest, CacheOperationResult
from ashare_alpha.data.cache.storage import cache_file_record, load_cache_manifest, save_cache_manifest, save_cache_validation_report
from ashare_alpha.data.cache.validator import ExternalCacheValidator
from ashare_alpha.data.contracts import ExternalContractValidator, ExternalFixtureConverter, save_conversion_result_json
from ashare_alpha.data.contracts.schemas import get_external_contracts
from ashare_alpha.importing.versioning import normalize_source_name, validate_data_version
from ashare_alpha.security.models import SecurityConfig


class ExternalCacheStore:
    def __init__(self, cache_root: Path = Path("data/cache/external"), config_dir: Path = Path("configs/ashare_alpha")) -> None:
        self.cache_root = Path(cache_root)
        self.config_dir = Path(config_dir)

    def cache_source_fixture(
        self,
        source_name: str,
        fixture_dir: Path,
        cache_version: str | None = None,
        overwrite: bool = False,
    ) -> CacheOperationResult:
        security = load_project_config(self.config_dir).security
        _assert_cache_operation_allowed(security)
        source_name = normalize_source_name(source_name)
        cache_version = cache_version or create_cache_version(source_name)
        validate_data_version(cache_version)
        cache_dir = self._cache_dir(source_name, cache_version)
        raw_dir = cache_dir / "raw"
        normalized_dir = cache_dir / "normalized"
        manifest_path = cache_dir / "cache_manifest.json"

        if cache_dir.exists() and not overwrite:
            raise ValueError(f"Cache already exists: {cache_dir}. Use --overwrite to replace it.")
        if cache_dir.exists() and overwrite:
            shutil.rmtree(cache_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)
        normalized_dir.mkdir(parents=True, exist_ok=True)

        fixture_dir = Path(fixture_dir)
        contract_report = ExternalContractValidator(source_name, fixture_dir).validate()
        if not contract_report.passed:
            errors = [issue.message for issue in contract_report.issues if issue.severity == "error"]
            manifest = self._manifest(
                source_name=source_name,
                cache_version=cache_version,
                cache_dir=cache_dir,
                raw_files=[],
                normalized_files=[],
                raw_contract_passed=False,
                normalized_validation_passed=None,
                normalized_row_counts={},
                validation_errors=errors,
                validation_warnings=[issue.message for issue in contract_report.issues if issue.severity != "error"],
                status="FAILED",
                error_message="External fixture contract validation failed: " + "; ".join(errors),
                mapping_path=None,
            )
            save_cache_manifest(manifest, manifest_path)
            return _result_from_manifest(manifest, manifest_path)

        raw_files = []
        for contract in get_external_contracts(source_name):
            source_path = fixture_dir / f"{contract.dataset_name}.csv"
            target_path = raw_dir / source_path.name
            shutil.copy2(source_path, target_path)
            raw_files.append(cache_file_record(contract.dataset_name, cache_dir, target_path))

        validation_report = ExternalCacheValidator(self.cache_root, source_name, cache_version).validate()
        save_cache_validation_report(validation_report, cache_dir / "validation_report.json")
        manifest = self._manifest(
            source_name=source_name,
            cache_version=cache_version,
            cache_dir=cache_dir,
            raw_files=raw_files,
            normalized_files=[],
            raw_contract_passed=validation_report.raw_contract_passed,
            normalized_validation_passed=None,
            normalized_row_counts={},
            validation_errors=validation_report.errors,
            validation_warnings=validation_report.warnings,
            status="RAW_CACHED" if validation_report.raw_contract_passed else "FAILED",
            error_message=None if validation_report.raw_contract_passed else "Raw cache validation failed.",
            mapping_path=None,
        )
        save_cache_manifest(manifest, manifest_path)
        return _result_from_manifest(manifest, manifest_path)

    def materialize_cache(
        self,
        source_name: str,
        cache_version: str,
        mapping_path: Path,
    ) -> CacheOperationResult:
        security = load_project_config(self.config_dir).security
        _assert_cache_operation_allowed(security)
        source_name = normalize_source_name(source_name)
        validate_data_version(cache_version)
        cache_dir = self._cache_dir(source_name, cache_version)
        raw_dir = cache_dir / "raw"
        normalized_dir = cache_dir / "normalized"
        manifest_path = cache_dir / "cache_manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"Cache manifest does not exist: {manifest_path}")

        previous = load_cache_manifest(manifest_path)
        normalized_dir.mkdir(parents=True, exist_ok=True)
        conversion = ExternalFixtureConverter(source_name, raw_dir, Path(mapping_path), normalized_dir).convert()
        save_conversion_result_json(conversion, cache_dir / "conversion_result.json")
        validation = LocalCsvAdapter(normalized_dir).validate_all()
        save_cache_validation_report(
            ExternalCacheValidator(self.cache_root, source_name, cache_version).validate(),
            cache_dir / "validation_report.json",
        )
        normalized_files = [
            cache_file_record(dataset_name, cache_dir, normalized_dir / filename)
            for dataset_name, filename in LocalCsvAdapter.FILES.items()
            if (normalized_dir / filename).exists()
        ]
        manifest = self._manifest(
            source_name=source_name,
            cache_version=cache_version,
            cache_dir=cache_dir,
            raw_files=previous.raw_files,
            normalized_files=normalized_files,
            raw_contract_passed=True,
            normalized_validation_passed=validation.passed,
            normalized_row_counts=validation.row_counts,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
            status="NORMALIZED" if validation.passed else "FAILED",
            error_message=None if validation.passed else "Normalized cache validation failed: " + "; ".join(validation.errors),
            mapping_path=str(mapping_path),
        )
        save_cache_manifest(manifest, manifest_path)
        return _result_from_manifest(manifest, manifest_path)

    def list_caches(self, source_name: str | None = None) -> list[CacheManifest]:
        source_filter = normalize_source_name(source_name) if source_name else None
        if not self.cache_root.exists():
            return []
        manifests = []
        for manifest_path in sorted(self.cache_root.glob("*/*/cache_manifest.json")):
            manifest = load_cache_manifest(manifest_path)
            if source_filter and manifest.source_name != source_filter:
                continue
            manifests.append(manifest)
        return manifests

    def inspect_cache(self, source_name: str, cache_version: str) -> CacheManifest:
        source_name = normalize_source_name(source_name)
        validate_data_version(cache_version)
        return load_cache_manifest(self._cache_dir(source_name, cache_version) / "cache_manifest.json")

    def validate_cache(self, source_name: str, cache_version: str) -> CacheOperationResult:
        report = ExternalCacheValidator(self.cache_root, source_name, cache_version).validate()
        cache_dir = Path(report.cache_dir)
        save_cache_validation_report(report, cache_dir / "validation_report.json")
        manifest = load_cache_manifest(cache_dir / "cache_manifest.json")
        updated = manifest.model_copy(
            update={
                "updated_at": datetime.now(),
                "raw_contract_passed": report.raw_contract_passed,
                "normalized_validation_passed": report.normalized_validation_passed,
                "normalized_row_counts": report.normalized_row_counts,
                "validation_errors": report.errors,
                "validation_warnings": report.warnings,
                "status": manifest.status if report.passed else "FAILED",
                "error_message": None if report.passed else "Cache validation failed.",
            }
        )
        save_cache_manifest(updated, cache_dir / "cache_manifest.json")
        return _result_from_manifest(updated, cache_dir / "cache_manifest.json")

    def _cache_dir(self, source_name: str, cache_version: str) -> Path:
        return self.cache_root / source_name / cache_version

    def _manifest(
        self,
        source_name: str,
        cache_version: str,
        cache_dir: Path,
        raw_files: list,
        normalized_files: list,
        raw_contract_passed: bool,
        normalized_validation_passed: bool | None,
        normalized_row_counts: dict[str, int],
        validation_errors: list[str],
        validation_warnings: list[str],
        status: str,
        error_message: str | None,
        mapping_path: str | None,
    ) -> CacheManifest:
        now = datetime.now()
        manifest_path = cache_dir / "cache_manifest.json"
        created_at = load_cache_manifest(manifest_path).created_at if manifest_path.exists() else now
        return CacheManifest(
            cache_id=build_cache_id(source_name, cache_version),
            source_name=source_name,
            cache_version=cache_version,
            created_at=created_at,
            updated_at=now,
            cache_dir=str(cache_dir),
            raw_dir=str(cache_dir / "raw"),
            normalized_dir=str(cache_dir / "normalized"),
            mapping_path=mapping_path,
            raw_files=raw_files,
            normalized_files=normalized_files,
            raw_contract_passed=raw_contract_passed,
            normalized_validation_passed=normalized_validation_passed,
            normalized_row_counts=normalized_row_counts,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            status=status,
            error_message=error_message,
            summary=_summary(status, source_name, cache_version),
        )


def _assert_cache_operation_allowed(security: SecurityConfig) -> None:
    if security.allow_network:
        raise RuntimeError("Cache operations must not enable network access.")
    if security.allow_broker_connections or security.allow_live_trading:
        raise RuntimeError("Cache operations must not enable broker or live trading capabilities.")


def _result_from_manifest(manifest: CacheManifest, manifest_path: Path) -> CacheOperationResult:
    return CacheOperationResult(
        source_name=manifest.source_name,
        cache_version=manifest.cache_version,
        cache_dir=manifest.cache_dir,
        status=manifest.status,
        manifest_path=str(manifest_path),
        raw_dir=manifest.raw_dir,
        normalized_dir=manifest.normalized_dir,
        raw_file_count=len(manifest.raw_files),
        normalized_file_count=len(manifest.normalized_files),
        validation_passed=manifest.normalized_validation_passed,
        error_message=manifest.error_message,
        summary=manifest.summary,
    )


def _summary(status: str, source_name: str, cache_version: str) -> str:
    if status == "RAW_CACHED":
        return f"{source_name}/{cache_version} raw cache is ready; no network was used."
    if status == "NORMALIZED":
        return f"{source_name}/{cache_version} cache has normalized standard tables."
    return f"{source_name}/{cache_version} cache operation failed."
