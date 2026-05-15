from __future__ import annotations

import shutil
from pathlib import Path

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.runtime import CacheOnlyAdapter, SourceProfile
from tests.test_source_runtime_context import _context


def test_cache_only_copies_standard_four_tables(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    shutil.copytree("data/sample/ashare_alpha", cache_dir)

    result = _adapter(_profile(cache_dir)).materialize(tmp_path / "out")

    assert result.status == "SUCCESS"
    assert LocalCsvAdapter(tmp_path / "out").validate_all().passed is True


def test_cache_only_missing_cache_dir_fails(tmp_path: Path) -> None:
    result = _adapter(_profile(tmp_path / "missing")).materialize(tmp_path / "out")

    assert result.status == "FAILED"
    assert "不会联网获取" in (result.error_message or "")


def test_cache_only_missing_table_fails(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    shutil.copytree("data/sample/ashare_alpha", cache_dir)
    (cache_dir / "daily_bar.csv").unlink()

    result = _adapter(_profile(cache_dir)).materialize(tmp_path / "out")

    assert result.status == "FAILED"
    assert "daily_bar.csv" in (result.error_message or "")


def test_cache_only_source_does_not_import_network_or_vendor_sdks() -> None:
    text = Path("src/ashare_alpha/data/runtime/cache.py").read_text(encoding="utf-8")

    assert "import requests" not in text
    assert "import httpx" not in text
    assert "import tushare" not in text
    assert "import akshare" not in text


def _profile(cache_dir: Path) -> SourceProfile:
    return SourceProfile.model_validate(
        {
            "source_name": "cache_only_test",
            "display_name": "Cache Only Test",
            "mode": "cache_only",
            "contract_source_name": "tushare_like",
            "mapping_path": "configs/ashare_alpha/data_sources/tushare_like_mapping.yaml",
            "fixture_dir": None,
            "cache_dir": str(cache_dir),
            "output_root_dir": "data/materialized",
            "data_version_prefix": "cache_only_test",
            "requires_network": False,
            "requires_api_key": False,
            "api_key_env_var": None,
            "enabled": True,
            "notes": None,
        }
    )


def _adapter(profile: SourceProfile) -> CacheOnlyAdapter:
    return CacheOnlyAdapter(_context(profile), data_version="cache_sample", config_dir=Path("configs/ashare_alpha"))
