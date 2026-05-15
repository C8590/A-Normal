from __future__ import annotations

from pathlib import Path

from ashare_alpha.data.adapters.local_csv import LocalCsvAdapter
from ashare_alpha.data.contracts import ExternalContractValidator, ExternalFixtureConverter
from ashare_alpha.data.runtime.external_base import ExternalDataRuntimeAdapter
from ashare_alpha.data.runtime.models import MaterializationResult
from ashare_alpha.data.runtime.storage import save_materialization_result_json


class OfflineReplayAdapter(ExternalDataRuntimeAdapter):
    def materialize(self, output_dir: Path) -> MaterializationResult:
        profile = self.context.profile
        output_dir = Path(output_dir)
        try:
            self.context.assert_can_run_offline()
            fixture_dir = Path(profile.fixture_dir or "")
            contract_report = ExternalContractValidator(profile.contract_source_name, fixture_dir).validate()
            if not contract_report.passed:
                errors = [issue.message for issue in contract_report.issues if issue.severity == "error"]
                return self._failed(
                    output_dir,
                    contract_passed=False,
                    error_message="契约检查失败，已跳过转换：" + "; ".join(errors),
                )

            conversion = ExternalFixtureConverter(
                source_name=profile.contract_source_name,
                fixture_dir=fixture_dir,
                mapping_path=Path(profile.mapping_path),
                output_dir=output_dir,
            ).convert()
            validation = LocalCsvAdapter(output_dir).validate_all()
            if not validation.passed:
                return self._failed(
                    output_dir,
                    contract_passed=True,
                    generated_files=conversion.generated_files,
                    row_counts=validation.row_counts,
                    validation_passed=False,
                    error_message="标准四表校验失败：" + "; ".join(validation.errors),
                )
            result = MaterializationResult(
                source_name=profile.source_name,
                contract_source_name=profile.contract_source_name,
                mode=profile.mode,
                output_dir=str(output_dir),
                data_version=self.data_version,
                generated_files=conversion.generated_files,
                row_counts=validation.row_counts,
                contract_passed=True,
                validation_passed=True,
                quality_passed=None,
                status="SUCCESS",
                error_message=None,
                summary=f"{profile.source_name} 离线 fixture 已 materialize 为标准四表。",
            )
        except Exception as exc:  # noqa: BLE001 - result files should explain operational failures.
            result = self._failed(output_dir, contract_passed=False, error_message=str(exc))
        save_materialization_result_json(result, output_dir / "materialization_result.json")
        return result

    def _failed(
        self,
        output_dir: Path,
        contract_passed: bool,
        error_message: str,
        generated_files: list[str] | None = None,
        row_counts: dict[str, int] | None = None,
        validation_passed: bool = False,
    ) -> MaterializationResult:
        profile = self.context.profile
        return MaterializationResult(
            source_name=profile.source_name,
            contract_source_name=profile.contract_source_name,
            mode=profile.mode,
            output_dir=str(output_dir),
            data_version=self.data_version,
            generated_files=generated_files or [],
            row_counts=row_counts or {},
            contract_passed=contract_passed,
            validation_passed=validation_passed,
            quality_passed=None,
            status="FAILED",
            error_message=error_message,
            summary=f"{profile.source_name} 离线 materialize 失败。",
        )
