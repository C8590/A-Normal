from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.data.adapters.local_csv import LocalCsvAdapter
from ashare_alpha.data.cache.models import CacheValidationReport
from ashare_alpha.data.contracts import ExternalContractValidator
from ashare_alpha.importing.versioning import normalize_source_name, validate_data_version


class ExternalCacheValidator:
    def __init__(self, cache_root: Path, source_name: str, cache_version: str) -> None:
        self.cache_root = Path(cache_root)
        self.source_name = normalize_source_name(source_name)
        self.cache_version = cache_version
        validate_data_version(cache_version)
        self.cache_dir = self.cache_root / self.source_name / self.cache_version
        self.raw_dir = self.cache_dir / "raw"
        self.normalized_dir = self.cache_dir / "normalized"

    def validate(self) -> CacheValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        contract_report = ExternalContractValidator(self.source_name, self.raw_dir).validate()
        raw_contract_passed = contract_report.passed
        errors.extend(issue.message for issue in contract_report.issues if issue.severity == "error")
        warnings.extend(issue.message for issue in contract_report.issues if issue.severity in {"warning", "info"})

        normalized_validation_passed: bool | None = None
        normalized_row_counts: dict[str, int] = {}
        has_normalized_files = any((self.normalized_dir / filename).exists() for filename in LocalCsvAdapter.FILES.values())
        if has_normalized_files:
            validation = LocalCsvAdapter(self.normalized_dir).validate_all()
            normalized_validation_passed = validation.passed
            normalized_row_counts = validation.row_counts
            errors.extend(validation.errors)
            warnings.extend(validation.warnings)
        else:
            warnings.append("Normalized cache has not been materialized yet.")

        passed = raw_contract_passed and (normalized_validation_passed is not False) and not errors
        summary = (
            f"External cache validation {'passed' if passed else 'failed'} for "
            f"{self.source_name}/{self.cache_version}."
        )
        return CacheValidationReport(
            source_name=self.source_name,
            cache_version=self.cache_version,
            generated_at=datetime.now(),
            cache_dir=str(self.cache_dir),
            raw_contract_passed=raw_contract_passed,
            normalized_validation_passed=normalized_validation_passed,
            passed=passed,
            errors=errors,
            warnings=warnings,
            raw_row_counts=contract_report.row_counts,
            normalized_row_counts=normalized_row_counts,
            summary=summary,
        )
