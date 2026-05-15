from __future__ import annotations

from pathlib import Path

import yaml

from ashare_alpha.data.runtime import SourceMaterializer


def test_source_materializer_runs_tushare_like_offline(tmp_path: Path) -> None:
    result = SourceMaterializer(
        profile_path=Path("configs/ashare_alpha/source_profiles/tushare_like_offline.yaml"),
        config_dir=Path("configs/ashare_alpha"),
        output_root_dir=tmp_path,
        data_version="contract_sample",
    ).run()

    assert result.status == "SUCCESS"
    assert Path(result.output_dir) == tmp_path / "tushare_like_offline" / "contract_sample"


def test_source_materializer_quality_report_generates_files(tmp_path: Path) -> None:
    result = SourceMaterializer(
        profile_path=Path("configs/ashare_alpha/source_profiles/tushare_like_offline.yaml"),
        config_dir=Path("configs/ashare_alpha"),
        output_root_dir=tmp_path,
        data_version="quality_sample",
        run_quality_report=True,
    ).run()

    output_dir = Path(result.output_dir)
    assert result.status == "SUCCESS"
    assert result.quality_passed is True
    assert (output_dir / "quality_report.json").exists()


def test_source_materializer_live_disabled_returns_failed(tmp_path: Path) -> None:
    profile_path = tmp_path / "live_disabled.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "source_name": "vendor_live",
                "display_name": "Vendor Live",
                "mode": "live_disabled",
                "contract_source_name": "tushare_like",
                "mapping_path": "configs/ashare_alpha/data_sources/tushare_like_mapping.yaml",
                "fixture_dir": None,
                "cache_dir": None,
                "output_root_dir": str(tmp_path),
                "data_version_prefix": "vendor_live",
                "requires_network": True,
                "requires_api_key": True,
                "api_key_env_var": "ASHARE_ALPHA_VENDOR_TOKEN",
                "enabled": True,
                "notes": "placeholder",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = SourceMaterializer(
        profile_path=profile_path,
        config_dir=Path("configs/ashare_alpha"),
        output_root_dir=tmp_path,
        data_version="live_sample",
    ).run()

    assert result.status == "FAILED"
    assert "live_disabled" in (result.error_message or "")


def test_source_materializer_output_root_can_be_overridden(tmp_path: Path) -> None:
    result = SourceMaterializer(
        profile_path=Path("configs/ashare_alpha/source_profiles/akshare_like_offline.yaml"),
        config_dir=Path("configs/ashare_alpha"),
        output_root_dir=tmp_path / "custom",
        data_version="custom_sample",
    ).run()

    assert Path(result.output_dir) == tmp_path / "custom" / "akshare_like_offline" / "custom_sample"
    assert result.status == "SUCCESS"
