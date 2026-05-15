from __future__ import annotations

import shutil
from pathlib import Path

from ashare_alpha.data.adapters.local_csv import LocalCsvAdapter
from ashare_alpha.data.runtime.external_base import ExternalDataRuntimeAdapter
from ashare_alpha.data.runtime.models import MaterializationResult
from ashare_alpha.data.runtime.storage import save_materialization_result_json


class CacheOnlyAdapter(ExternalDataRuntimeAdapter):
    def materialize(self, output_dir: Path) -> MaterializationResult:
        profile = self.context.profile
        output_dir = Path(output_dir)
        try:
            self.context.assert_can_run_offline()
            cache_dir = Path(profile.cache_dir or "")
            missing = _missing_standard_tables(cache_dir)
            if not cache_dir.exists() or missing:
                detail = f"缺少文件：{', '.join(missing)}" if missing else f"缓存目录不存在：{cache_dir}"
                result = self._failed(output_dir, f"cache_only 模式需要本地缓存四表，不会联网获取。{detail}")
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                generated_files: list[str] = []
                for filename in LocalCsvAdapter.FILES.values():
                    target = output_dir / filename
                    shutil.copy2(cache_dir / filename, target)
                    generated_files.append(str(target))
                validation = LocalCsvAdapter(output_dir).validate_all()
                if validation.passed:
                    result = MaterializationResult(
                        source_name=profile.source_name,
                        contract_source_name=profile.contract_source_name,
                        mode=profile.mode,
                        output_dir=str(output_dir),
                        data_version=self.data_version,
                        generated_files=generated_files,
                        row_counts=validation.row_counts,
                        contract_passed=True,
                        validation_passed=True,
                        quality_passed=None,
                        status="SUCCESS",
                        error_message=None,
                        summary=f"{profile.source_name} 本地缓存四表已复制并校验通过。",
                    )
                else:
                    result = self._failed(
                        output_dir,
                        "本地缓存四表校验失败：" + "; ".join(validation.errors),
                        generated_files=generated_files,
                        row_counts=validation.row_counts,
                    )
        except Exception as exc:  # noqa: BLE001 - result files should explain operational failures.
            result = self._failed(output_dir, str(exc))
        save_materialization_result_json(result, output_dir / "materialization_result.json")
        return result

    def _failed(
        self,
        output_dir: Path,
        error_message: str,
        generated_files: list[str] | None = None,
        row_counts: dict[str, int] | None = None,
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
            contract_passed=True,
            validation_passed=False,
            quality_passed=None,
            status="FAILED",
            error_message=error_message,
            summary=f"{profile.source_name} cache_only materialize 失败。",
        )


def _missing_standard_tables(cache_dir: Path) -> list[str]:
    if not cache_dir.exists() or not cache_dir.is_dir():
        return []
    return [filename for filename in LocalCsvAdapter.FILES.values() if not (cache_dir / filename).is_file()]
