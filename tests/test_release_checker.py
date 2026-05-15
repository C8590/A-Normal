from __future__ import annotations

from pathlib import Path

from ashare_alpha import __version__
from ashare_alpha.release import ReleaseChecker


def test_version_file_exists_and_matches_runtime_version() -> None:
    version = Path("VERSION").read_text(encoding="utf-8").strip()

    assert version == "0.1.0-mvp"
    assert __version__ == version


def test_release_documents_contain_version() -> None:
    version = Path("VERSION").read_text(encoding="utf-8").strip()

    assert version in Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert version in Path("RELEASE_NOTES.md").read_text(encoding="utf-8")


def test_release_checker_runs_on_current_project() -> None:
    manifest = ReleaseChecker(Path.cwd()).run()

    assert manifest.version == "0.1.0-mvp"
    assert manifest.fail_count == 0
    assert manifest.checks_passed is True


def test_release_checker_finds_missing_files(tmp_path: Path) -> None:
    project_root, package_dir = _write_minimal_release_project(tmp_path)
    (project_root / "README.md").unlink()

    manifest = ReleaseChecker(project_root, package_dir=package_dir).run()

    assert manifest.fail_count > 0
    assert any(item.status == "FAIL" and "README.md" in item.name for item in manifest.checks)


def test_release_checker_finds_unsafe_allow_network(tmp_path: Path) -> None:
    project_root, package_dir = _write_minimal_release_project(tmp_path)
    security_path = project_root / "configs" / "ashare_alpha" / "security.yaml"
    security_path.write_text(
        "\n".join(
            [
                "offline_mode: true",
                "allow_network: true",
                "allow_broker_connections: false",
                "allow_live_trading: false",
            ]
        ),
        encoding="utf-8",
    )

    manifest = ReleaseChecker(project_root, package_dir=package_dir).run()

    assert any(item.status == "FAIL" and item.name == "安全配置开关" for item in manifest.checks)


def test_release_checker_finds_forbidden_import_in_temp_source(tmp_path: Path) -> None:
    project_root, package_dir = _write_minimal_release_project(tmp_path)
    (package_dir / "bad_adapter.py").write_text("import " + "requests\n", encoding="utf-8")

    manifest = ReleaseChecker(project_root, package_dir=package_dir).run()

    assert any(item.status == "FAIL" and item.name == "禁用依赖扫描" for item in manifest.checks)


def _write_minimal_release_project(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path
    package_dir = project_root / "src" / "ashare_alpha"
    config_dir = project_root / "configs" / "ashare_alpha"
    docs_dir = project_root / "docs"
    scripts_dir = project_root / "scripts"
    outputs_dev_dir = project_root / "outputs" / "dev"
    package_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    docs_dir.mkdir()
    scripts_dir.mkdir()
    outputs_dev_dir.mkdir(parents=True)

    (project_root / "VERSION").write_text("0.1.0-mvp", encoding="utf-8")
    (project_root / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0-mvp\n", encoding="utf-8")
    (project_root / "RELEASE_NOTES.md").write_text("# 0.1.0-mvp\n", encoding="utf-8")
    (project_root / "README.md").write_text("# README\n", encoding="utf-8")
    (project_root / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.1.0'\n", encoding="utf-8")
    (docs_dir / "COMMAND_MATRIX.md").write_text("# Command Matrix\n", encoding="utf-8")
    (docs_dir / "DEVELOPMENT_SETUP.md").write_text("# Dev\n", encoding="utf-8")
    (scripts_dir / "dev_check.py").write_text("print('ok')\n", encoding="utf-8")
    (scripts_dir / "smoke_test.py").write_text("print('ok')\n", encoding="utf-8")
    (outputs_dev_dir / "smoke_test_report.json").write_text("{}", encoding="utf-8")
    (outputs_dev_dir / "command_matrix.json").write_text("{}", encoding="utf-8")
    (package_dir / "__init__.py").write_text('__version__ = "0.1.0-mvp"\n', encoding="utf-8")
    (config_dir / "security.yaml").write_text(
        "\n".join(
            [
                "offline_mode: true",
                "allow_network: false",
                "allow_broker_connections: false",
                "allow_live_trading: false",
            ]
        ),
        encoding="utf-8",
    )
    return project_root, package_dir
