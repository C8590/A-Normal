from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.config import load_project_config, load_yaml_config
from ashare_alpha.data.runtime.cache import CacheOnlyAdapter
from ashare_alpha.data.runtime.context import SourceRuntimeContext
from ashare_alpha.data.runtime.models import MaterializationResult, SourceProfile
from ashare_alpha.data.runtime.offline_replay import OfflineReplayAdapter
from ashare_alpha.data.runtime.storage import save_materialization_result_json
from ashare_alpha.quality import DataQualityReporter, save_quality_issues_csv, save_quality_report_json, save_quality_report_md
from ashare_alpha.security import EnvSecretProvider, NetworkGuard


class SourceMaterializer:
    def __init__(
        self,
        profile_path: Path,
        config_dir: Path,
        output_root_dir: Path | None = None,
        data_version: str | None = None,
        run_quality_report: bool = False,
    ) -> None:
        self.profile_path = Path(profile_path)
        self.config_dir = Path(config_dir)
        self.output_root_dir = Path(output_root_dir) if output_root_dir is not None else None
        self.data_version = data_version
        self.run_quality_report = run_quality_report

    def run(self) -> MaterializationResult:
        project_config = load_project_config(self.config_dir)
        profile = SourceProfile.model_validate(load_yaml_config(self.profile_path))
        data_version = self.data_version or _default_data_version(profile)
        output_root = self.output_root_dir or Path(profile.output_root_dir)
        output_dir = output_root / profile.source_name / data_version
        context = SourceRuntimeContext(
            profile=profile,
            security_config=project_config.security,
            network_guard=NetworkGuard(project_config.security),
            secret_provider=EnvSecretProvider(),
        )

        if profile.mode == "live_disabled":
            result = MaterializationResult(
                source_name=profile.source_name,
                contract_source_name=profile.contract_source_name,
                mode=profile.mode,
                output_dir=str(output_dir),
                data_version=data_version,
                generated_files=[],
                row_counts={},
                contract_passed=False,
                validation_passed=False,
                quality_passed=None,
                status="FAILED",
                error_message=f"live_disabled 只是联网占位模式，当前不能运行：{profile.source_name}",
                summary=f"{profile.source_name} 未运行。",
            )
            save_materialization_result_json(result, output_dir / "materialization_result.json")
            return result

        adapter = (
            OfflineReplayAdapter(context, data_version=data_version, config_dir=self.config_dir)
            if profile.mode == "offline_replay"
            else CacheOnlyAdapter(context, data_version=data_version, config_dir=self.config_dir)
        )
        result = adapter.materialize(output_dir)
        if self.run_quality_report and result.status == "SUCCESS":
            quality = DataQualityReporter(
                data_dir=output_dir,
                config_dir=self.config_dir,
                source_name=profile.source_name,
                data_version=data_version,
            ).run()
            save_quality_report_json(quality, output_dir / "quality_report.json")
            save_quality_report_md(quality, output_dir / "quality_report.md")
            save_quality_issues_csv(quality, output_dir / "quality_issues.csv")
            result = result.model_copy(
                update={
                    "quality_passed": quality.passed,
                    "status": "SUCCESS" if quality.passed else "FAILED",
                    "error_message": None if quality.passed else "数据质量报告存在 error 级问题。",
                    "summary": (
                        f"{profile.source_name} materialize 完成，质量报告通过。"
                        if quality.passed
                        else f"{profile.source_name} materialize 完成，但质量报告未通过。"
                    ),
                }
            )
        save_materialization_result_json(result, output_dir / "materialization_result.json")
        return result


def _default_data_version(profile: SourceProfile) -> str:
    prefix = profile.data_version_prefix or profile.source_name
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
