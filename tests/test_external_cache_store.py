from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.cache import ExternalCacheStore, ExternalCacheValidator, load_cache_manifest
from ashare_alpha.importing import ImportJob
from ashare_alpha.pipeline import PipelineRunner


def test_cache_source_fixture_creates_raw_manifest(tmp_path: Path) -> None:
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=Path("configs/ashare_alpha"))

    result = store.cache_source_fixture(
        source_name="tushare_like",
        fixture_dir=Path("tests/fixtures/external_sources/tushare_like"),
        cache_version="fixture_v1",
    )

    assert result.status == "RAW_CACHED"
    manifest = load_cache_manifest(Path(result.manifest_path))
    assert manifest.source_name == "tushare_like"
    assert len(manifest.raw_files) == 4
    assert (Path(result.raw_dir) / "stock_basic.csv").exists()
    assert (Path(result.cache_dir) / "validation_report.json").exists()


def test_materialize_cache_outputs_valid_standard_tables(tmp_path: Path) -> None:
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=Path("configs/ashare_alpha"))
    store.cache_source_fixture(
        source_name="akshare_like",
        fixture_dir=Path("tests/fixtures/external_sources/akshare_like"),
        cache_version="fixture_v1",
    )

    result = store.materialize_cache(
        source_name="akshare_like",
        cache_version="fixture_v1",
        mapping_path=Path("configs/ashare_alpha/data_sources/akshare_like_mapping.yaml"),
    )

    assert result.status == "NORMALIZED"
    validation = LocalCsvAdapter(Path(result.normalized_dir)).validate_all()
    assert validation.passed is True
    manifest = load_cache_manifest(Path(result.manifest_path))
    assert manifest.normalized_validation_passed is True
    assert len(manifest.normalized_files) == 4


def test_cache_validator_allows_raw_only_cache(tmp_path: Path) -> None:
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=Path("configs/ashare_alpha"))
    store.cache_source_fixture(
        source_name="tushare_like",
        fixture_dir=Path("tests/fixtures/external_sources/tushare_like"),
        cache_version="raw_only",
    )

    report = ExternalCacheValidator(tmp_path / "cache", "tushare_like", "raw_only").validate()

    assert report.raw_contract_passed is True
    assert report.normalized_validation_passed is None
    assert report.passed is True


def test_materialized_cache_can_import_and_run_pipeline(tmp_path: Path) -> None:
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=Path("configs/ashare_alpha"))
    store.cache_source_fixture(
        source_name="tushare_like",
        fixture_dir=Path("tests/fixtures/external_sources/tushare_like"),
        cache_version="pipeline_v1",
    )
    cache_result = store.materialize_cache(
        source_name="tushare_like",
        cache_version="pipeline_v1",
        mapping_path=Path("configs/ashare_alpha/data_sources/tushare_like_mapping.yaml"),
    )

    import_manifest = ImportJob(
        source_name="tushare_like",
        source_data_dir=Path(cache_result.normalized_dir),
        target_root_dir=tmp_path / "imports",
        data_version="pipeline_v1",
        config_dir=Path("configs/ashare_alpha"),
        quality_report=True,
    ).run()
    assert import_manifest.status == "SUCCESS"

    pipeline_manifest = PipelineRunner(
        date=date(2026, 3, 20),
        data_dir=Path(import_manifest.target_data_dir),
        config_dir=Path("configs/ashare_alpha"),
        output_dir=tmp_path / "pipeline",
        audit_leakage=True,
        quality_report=True,
        check_security=True,
    ).run()
    assert pipeline_manifest.status == "SUCCESS"


def test_cache_manifest_json_is_machine_readable(tmp_path: Path) -> None:
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=Path("configs/ashare_alpha"))
    result = store.cache_source_fixture(
        source_name="tushare_like",
        fixture_dir=Path("tests/fixtures/external_sources/tushare_like"),
        cache_version="readable",
    )

    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert payload["cache_id"] == "tushare_like_readable"
    assert payload["status"] == "RAW_CACHED"


def test_cache_source_fixture_rejects_enabled_network(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    shutil.copytree("configs/ashare_alpha", config_dir)
    security_path = config_dir / "security.yaml"
    security_text = security_path.read_text(encoding="utf-8").replace("allow_network: false", "allow_network: true")
    security_path.write_text(security_text, encoding="utf-8")
    store = ExternalCacheStore(cache_root=tmp_path / "cache", config_dir=config_dir)

    with pytest.raises(Exception, match="allow_network"):
        store.cache_source_fixture(
            source_name="tushare_like",
            fixture_dir=Path("tests/fixtures/external_sources/tushare_like"),
            cache_version="unsafe",
        )
