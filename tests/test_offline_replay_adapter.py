from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.runtime import OfflineReplayAdapter, SourceProfile
from tests.test_source_runtime_context import _context


def test_tushare_like_offline_materializes_standard_four_tables(tmp_path: Path) -> None:
    result = _adapter(_profile("tushare_like_offline", "tushare_like")).materialize(tmp_path / "out")

    assert result.status == "SUCCESS"
    assert {path.name for path in (tmp_path / "out").glob("*.csv")} == set(LocalCsvAdapter.FILES.values())


def test_akshare_like_offline_materializes_standard_four_tables(tmp_path: Path) -> None:
    result = _adapter(_profile("akshare_like_offline", "akshare_like")).materialize(tmp_path / "out")

    assert result.status == "SUCCESS"
    assert result.row_counts["daily_bar"] == 240


def test_contract_failure_returns_failed_without_conversion(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "bad_fixture"
    shutil.copytree("tests/fixtures/external_sources/tushare_like", fixture_dir)
    rows = _read_rows(fixture_dir / "daily.csv")
    fieldnames = [field for field in rows[0] if field != "ts_code"]
    _write_rows(fixture_dir / "daily.csv", [{key: row[key] for key in fieldnames} for row in rows], fieldnames)
    profile = _profile("bad_tushare_like", "tushare_like", fixture_dir=fixture_dir)

    result = _adapter(profile).materialize(tmp_path / "out")

    assert result.status == "FAILED"
    assert result.contract_passed is False
    assert not (tmp_path / "out" / "stock_master.csv").exists()


def test_materialized_output_validates_with_local_csv_adapter(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    _adapter(_profile("tushare_like_offline", "tushare_like")).materialize(output_dir)

    assert LocalCsvAdapter(output_dir).validate_all().passed is True


def test_runtime_source_does_not_import_network_or_vendor_sdks() -> None:
    banned_imports = ("import requests", "import httpx", "import tushare", "import akshare")
    for path in Path("src/ashare_alpha").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in banned_imports), path


def _profile(source_name: str, contract_source_name: str, fixture_dir: Path | None = None) -> SourceProfile:
    return SourceProfile.model_validate(
        {
            "source_name": source_name,
            "display_name": source_name,
            "mode": "offline_replay",
            "contract_source_name": contract_source_name,
            "mapping_path": f"configs/ashare_alpha/data_sources/{contract_source_name}_mapping.yaml",
            "fixture_dir": str(fixture_dir or Path("tests/fixtures/external_sources") / contract_source_name),
            "cache_dir": f"data/cache/external/{contract_source_name}",
            "output_root_dir": "data/materialized",
            "data_version_prefix": contract_source_name,
            "requires_network": False,
            "requires_api_key": False,
            "api_key_env_var": None,
            "enabled": True,
            "notes": None,
        }
    )


def _adapter(profile: SourceProfile) -> OfflineReplayAdapter:
    return OfflineReplayAdapter(_context(profile), data_version="contract_sample", config_dir=Path("configs/ashare_alpha"))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
