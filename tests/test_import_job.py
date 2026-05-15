from __future__ import annotations

import shutil
from pathlib import Path

from ashare_alpha.importing import ImportJob


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_sample_data_imports_successfully(tmp_path: Path) -> None:
    manifest = _job(tmp_path).run()
    target_dir = tmp_path / "imports" / "local_csv" / "sample_v1"

    assert manifest.status == "SUCCESS"
    assert (target_dir / "stock_master.csv").exists()
    assert (target_dir / "daily_bar.csv").exists()
    assert (target_dir / "financial_summary.csv").exists()
    assert (target_dir / "announcement_event.csv").exists()
    assert (target_dir / "import_manifest.json").exists()
    assert (target_dir / "validation_report.json").exists()
    assert (target_dir / "data_snapshot.json").exists()
    assert manifest.row_counts["stock_master"] == 12
    assert all(item.sha256 for item in manifest.copied_files)


def test_missing_source_data_dir_fails(tmp_path: Path) -> None:
    manifest = ImportJob(
        source_name="local_csv",
        source_data_dir=tmp_path / "missing",
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
    ).run()

    assert manifest.status == "FAILED"
    assert "源数据目录不存在" in manifest.error_message


def test_missing_required_csv_fails(tmp_path: Path) -> None:
    source_dir = _copy_sample(tmp_path / "source")
    (source_dir / "daily_bar.csv").unlink()

    manifest = ImportJob(
        source_name="local_csv",
        source_data_dir=source_dir,
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
    ).run()

    assert manifest.status == "FAILED"
    assert "缺少必要 CSV 文件" in manifest.error_message


def test_existing_target_without_overwrite_fails(tmp_path: Path) -> None:
    assert _job(tmp_path).run().status == "SUCCESS"

    manifest = _job(tmp_path).run()

    assert manifest.status == "FAILED"
    assert "目标导入目录已存在" in manifest.error_message


def test_overwrite_allows_existing_target(tmp_path: Path) -> None:
    assert _job(tmp_path).run().status == "SUCCESS"

    manifest = _job(tmp_path, overwrite=True).run()

    assert manifest.status == "SUCCESS"


def test_validation_failure_saves_manifest_and_validation_report(tmp_path: Path) -> None:
    source_dir = _copy_sample(tmp_path / "source")
    (source_dir / "daily_bar.csv").write_text(
        "trade_date,ts_code,open,high,low,close,pre_close,volume,amount,is_trading\n",
        encoding="utf-8",
    )
    manifest = ImportJob(
        source_name="local_csv",
        source_data_dir=source_dir,
        target_root_dir=tmp_path / "imports",
        data_version="bad_v1",
        config_dir=CONFIG_DIR,
    ).run()
    target_dir = tmp_path / "imports" / "local_csv" / "bad_v1"

    assert manifest.status == "FAILED"
    assert manifest.validation_passed is False
    assert (target_dir / "import_manifest.json").exists()
    assert (target_dir / "validation_report.json").exists()
    assert not (target_dir / "data_snapshot.json").exists()


def test_target_data_dir_cannot_equal_source_data_dir(tmp_path: Path) -> None:
    source_dir = tmp_path / "imports" / "local_csv" / "sample_v1"
    _copy_sample(source_dir)

    manifest = ImportJob(
        source_name="local_csv",
        source_data_dir=source_dir,
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
        overwrite=True,
    ).run()

    assert manifest.status == "FAILED"
    assert "不允许等于源数据目录" in manifest.error_message


def _job(tmp_path: Path, overwrite: bool = False) -> ImportJob:
    return ImportJob(
        source_name="local_csv",
        source_data_dir=DATA_DIR,
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
        overwrite=overwrite,
    )


def _copy_sample(target_dir: Path) -> Path:
    shutil.copytree(DATA_DIR, target_dir)
    return target_dir

