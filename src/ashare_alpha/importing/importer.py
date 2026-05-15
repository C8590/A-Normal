from __future__ import annotations

import csv
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from ashare_alpha.audit import build_data_snapshot, save_data_snapshot_json
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.importing.models import ImportedFile, ImportManifest
from ashare_alpha.importing.storage import compute_file_sha256, save_import_manifest, save_validation_report
from ashare_alpha.importing.versioning import create_data_version, normalize_source_name, validate_data_version
from ashare_alpha.quality import (
    DataQualityReporter,
    save_quality_issues_csv,
    save_quality_report_json,
    save_quality_report_md,
)


class ImportJob:
    def __init__(
        self,
        source_name: str,
        source_data_dir: Path,
        target_root_dir: Path = Path("data/imports"),
        data_version: str | None = None,
        config_dir: Path = Path("configs/ashare_alpha"),
        overwrite: bool = False,
        notes: str | None = None,
        quality_report: bool = False,
    ) -> None:
        self.raw_source_name = source_name
        self.source_data_dir = Path(source_data_dir)
        self.target_root_dir = Path(target_root_dir)
        self.data_version = data_version
        self.config_dir = Path(config_dir)
        self.overwrite = overwrite
        self.notes = notes
        self.quality_report = quality_report

    def run(self) -> ImportManifest:
        source_name = normalize_source_name(self.raw_source_name)
        data_version = self.data_version or create_data_version()
        validate_data_version(data_version)
        target_data_dir = self.target_root_dir / source_name / data_version
        in_place_import = self._allows_in_place_import() and self._is_in_place_import(target_data_dir)

        if target_data_dir.exists() and not self.overwrite:
            return self._failed_manifest(
                source_name=source_name,
                data_version=data_version,
                target_data_dir=target_data_dir,
                message=f"目标导入目录已存在：{target_data_dir}。如需覆盖请使用 --overwrite。",
            )

        try:
            self._validate_paths(target_data_dir)
            if target_data_dir.exists() and self.overwrite and not in_place_import:
                shutil.rmtree(target_data_dir)
            target_data_dir.mkdir(parents=True, exist_ok=True)

            copied_files = (
                self._record_existing_files(target_data_dir)
                if in_place_import
                else self._copy_required_files(target_data_dir)
            )
            adapter = LocalCsvAdapter(target_data_dir)
            validation_report = adapter.validate_all()
            save_validation_report(validation_report, target_data_dir / "validation_report.json")

            snapshot_id: str | None = None
            snapshot_path: str | None = None
            status = "SUCCESS" if validation_report.passed else "FAILED"
            error_message = None if validation_report.passed else "数据校验失败：" + "；".join(validation_report.errors)

            if validation_report.passed:
                snapshot = build_data_snapshot(
                    data_dir=target_data_dir,
                    config_dir=self.config_dir,
                    source_name=source_name,
                    data_version=data_version,
                    stock_master=adapter.load_stock_master(),
                    daily_bars=adapter.load_daily_bars(),
                    financial_summary=adapter.load_financial_summary(),
                    announcement_events=adapter.load_announcement_events(),
                    notes=self.notes,
                )
                snapshot_file = target_data_dir / "data_snapshot.json"
                save_data_snapshot_json(snapshot, snapshot_file)
                snapshot_id = snapshot.snapshot_id
                snapshot_path = str(snapshot_file)

            manifest_notes = self.notes
            if validation_report.passed and self.quality_report:
                quality = DataQualityReporter(
                    data_dir=target_data_dir,
                    config_dir=self.config_dir,
                    source_name=source_name,
                    data_version=data_version,
                ).run()
                save_quality_report_json(quality, target_data_dir / "quality_report.json")
                save_quality_report_md(quality, target_data_dir / "quality_report.md")
                save_quality_issues_csv(quality, target_data_dir / "quality_issues.csv")
                if quality.error_count > 0:
                    manifest_notes = _append_note(manifest_notes, "质量报告存在 error，请检查。")

            manifest = ImportManifest(
                import_id=_new_import_id(source_name, data_version),
                source_name=source_name,
                data_version=data_version,
                created_at=datetime.now(),
                source_data_dir=str(self.source_data_dir),
                target_data_dir=str(target_data_dir),
                config_dir=str(self.config_dir),
                copied_files=copied_files,
                row_counts=validation_report.row_counts,
                validation_passed=validation_report.passed,
                validation_error_count=len(validation_report.errors),
                validation_warning_count=len(validation_report.warnings),
                snapshot_id=snapshot_id,
                snapshot_path=snapshot_path,
                status=status,
                error_message=error_message,
                notes=manifest_notes,
            )
            save_import_manifest(manifest, target_data_dir / "import_manifest.json")
            return manifest
        except Exception as exc:  # noqa: BLE001 - import manifest should capture operational failures.
            manifest = self._failed_manifest(
                source_name=source_name,
                data_version=data_version,
                target_data_dir=target_data_dir,
                message=f"导入失败：{exc}",
            )
            if target_data_dir.exists():
                save_import_manifest(manifest, target_data_dir / "import_manifest.json")
            return manifest

    def _validate_paths(self, target_data_dir: Path) -> None:
        if not self.source_data_dir.exists():
            raise ValueError(f"源数据目录不存在：{self.source_data_dir}")
        if not self.source_data_dir.is_dir():
            raise ValueError(f"源数据路径不是目录：{self.source_data_dir}")
        source_resolved = self.source_data_dir.resolve()
        target_resolved = target_data_dir.resolve()
        if source_resolved == target_resolved and not self._allows_in_place_import():
            raise ValueError("目标导入目录不允许等于源数据目录")
        for filename in LocalCsvAdapter.FILES.values():
            path = self.source_data_dir / filename
            if not path.exists():
                raise ValueError(f"缺少必要 CSV 文件：{path}")
            if not path.is_file():
                raise ValueError(f"必要 CSV 路径不是文件：{path}")

    def _is_in_place_import(self, target_data_dir: Path) -> bool:
        try:
            return self.source_data_dir.resolve() == target_data_dir.resolve()
        except OSError:
            return False

    def _allows_in_place_import(self) -> bool:
        return self.overwrite and normalize_source_name(self.raw_source_name) in {"tushare_like", "akshare_like"}

    def _copy_required_files(self, target_data_dir: Path) -> list[ImportedFile]:
        copied_files: list[ImportedFile] = []
        for dataset_name, filename in LocalCsvAdapter.FILES.items():
            source_path = self.source_data_dir / filename
            target_path = target_data_dir / filename
            shutil.copy2(source_path, target_path)
            copied_files.append(
                ImportedFile(
                    dataset_name=dataset_name,
                    source_path=str(source_path),
                    target_path=str(target_path),
                    rows=_count_csv_rows(target_path),
                    sha256=compute_file_sha256(target_path),
                    copied=True,
                )
            )
        return copied_files

    def _record_existing_files(self, target_data_dir: Path) -> list[ImportedFile]:
        imported_files: list[ImportedFile] = []
        for dataset_name, filename in LocalCsvAdapter.FILES.items():
            path = target_data_dir / filename
            imported_files.append(
                ImportedFile(
                    dataset_name=dataset_name,
                    source_path=str(path),
                    target_path=str(path),
                    rows=_count_csv_rows(path),
                    sha256=compute_file_sha256(path),
                    copied=False,
                )
            )
        return imported_files

    def _failed_manifest(
        self,
        source_name: str,
        data_version: str,
        target_data_dir: Path,
        message: str,
    ) -> ImportManifest:
        return ImportManifest(
            import_id=_new_import_id(source_name, data_version),
            source_name=source_name,
            data_version=data_version,
            created_at=datetime.now(),
            source_data_dir=str(self.source_data_dir),
            target_data_dir=str(target_data_dir),
            config_dir=str(self.config_dir),
            copied_files=[],
            row_counts={},
            validation_passed=False,
            validation_error_count=1,
            validation_warning_count=0,
            snapshot_id=None,
            snapshot_path=None,
            status="FAILED",
            error_message=message,
            notes=self.notes,
        )


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def _new_import_id(source_name: str, data_version: str) -> str:
    return f"{source_name}_{data_version}_{uuid.uuid4().hex[:8]}"


def _append_note(notes: str | None, message: str) -> str:
    if not notes:
        return message
    return f"{notes} {message}"
