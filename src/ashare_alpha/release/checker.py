from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha.config import load_yaml_config
from ashare_alpha.release.models import ReleaseCheckItem, ReleaseManifest


KEY_FILES = (
    "VERSION",
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
    "README.md",
    "docs/COMMAND_MATRIX.md",
    "docs/DEVELOPMENT_SETUP.md",
    "configs/ashare_alpha/security.yaml",
    "scripts/dev_check.py",
    "scripts/smoke_test.py",
    "outputs/dev/smoke_test_report.json",
    "outputs/dev/command_matrix.json",
    "pyproject.toml",
)

KEY_COMMANDS = {
    "show_version": "python -m ashare_alpha show-version",
    "show_version_json": "python -m ashare_alpha show-version --format json",
    "release_check": "python -m ashare_alpha release-check",
    "release_check_json": "python -m ashare_alpha release-check --format json",
    "dev_check": "python scripts/dev_check.py",
    "smoke_test": "python scripts/smoke_test.py",
    "pytest": "pytest",
    "ruff": "ruff check",
    "pipeline_full": (
        "python -m ashare_alpha run-pipeline --date 2026-03-20 "
        "--audit-leakage --quality-report --check-security"
    ),
    "dashboard": "python -m ashare_alpha build-dashboard",
}


class ReleaseChecker:
    def __init__(
        self,
        project_root: Path | None = None,
        package_dir: Path | None = None,
        config_dir: Path | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.package_dir = Path(package_dir or self.project_root / "src" / "ashare_alpha")
        self.config_dir = Path(config_dir or self.project_root / "configs" / "ashare_alpha")

    def run(self) -> ReleaseManifest:
        checks: list[ReleaseCheckItem] = []
        key_files = {file_name: (self.project_root / file_name).exists() for file_name in KEY_FILES}

        self._check_key_file("VERSION", key_files, checks, required=True)
        self._check_key_file("CHANGELOG.md", key_files, checks, required=True)
        self._check_key_file("RELEASE_NOTES.md", key_files, checks, required=True)
        self._check_key_file("README.md", key_files, checks, required=True)
        self._check_key_file("docs/COMMAND_MATRIX.md", key_files, checks, required=True)
        self._check_key_file("docs/DEVELOPMENT_SETUP.md", key_files, checks, required=True)
        self._check_key_file("configs/ashare_alpha/security.yaml", key_files, checks, required=True)
        self._check_security_config(checks)
        self._check_forbidden_source_text(checks)
        self._check_key_file("scripts/dev_check.py", key_files, checks, required=True)
        self._check_key_file("scripts/smoke_test.py", key_files, checks, required=True)
        self._check_optional_artifact("outputs/dev/smoke_test_report.json", key_files, checks)
        self._check_optional_artifact("outputs/dev/command_matrix.json", key_files, checks)
        self._check_pytest_available(checks)
        self._check_ruff_available(checks)
        self._check_key_file("pyproject.toml", key_files, checks, required=True)
        version = self._read_version()
        self._check_runtime_version(version, checks)
        self._check_document_contains_version("CHANGELOG.md", version, checks)
        self._check_document_contains_version("RELEASE_NOTES.md", version, checks)
        self._check_live_order_names(checks)

        pass_count = sum(1 for item in checks if item.status == "PASS")
        warn_count = sum(1 for item in checks if item.status == "WARN")
        fail_count = sum(1 for item in checks if item.status == "FAIL")
        checks_passed = fail_count == 0
        summary = (
            f"发布检查{'通过' if checks_passed else '未通过'}："
            f"PASS={pass_count}, WARN={warn_count}, FAIL={fail_count}。"
        )
        return ReleaseManifest(
            version=version,
            generated_at=datetime.now(),
            project_root=str(self.project_root),
            python_version=sys.version.split()[0],
            checks_passed=checks_passed,
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
            checks=checks,
            key_files=key_files,
            key_commands=KEY_COMMANDS,
            safety_summary=self._safety_summary(),
            summary=summary,
        )

    def _check_key_file(
        self,
        file_name: str,
        key_files: dict[str, bool],
        checks: list[ReleaseCheckItem],
        *,
        required: bool,
    ) -> None:
        exists = key_files[file_name]
        checks.append(
            ReleaseCheckItem(
                name=f"关键文件：{file_name}",
                status="PASS" if exists else ("FAIL" if required else "WARN"),
                message=f"{file_name} {'存在' if exists else '不存在'}。",
                recommendation=None if exists else f"请补齐 {file_name}。",
            )
        )

    def _check_optional_artifact(
        self,
        file_name: str,
        key_files: dict[str, bool],
        checks: list[ReleaseCheckItem],
    ) -> None:
        path = self.project_root / file_name
        if not key_files[file_name]:
            checks.append(
                ReleaseCheckItem(
                    name=f"开发产物：{file_name}",
                    status="WARN",
                    message=f"{file_name} 不存在，可能尚未运行对应开发检查。",
                    recommendation="发布前建议运行 scripts/dev_check.py 或 scripts/smoke_test.py。",
                )
            )
            return
        checks.append(
            ReleaseCheckItem(
                name=f"开发产物：{file_name}",
                status="PASS",
                message=f"{file_name} 存在，最近修改时间 {datetime.fromtimestamp(path.stat().st_mtime).isoformat()}。",
                recommendation=None,
            )
        )

    def _check_security_config(self, checks: list[ReleaseCheckItem]) -> None:
        path = self.config_dir / "security.yaml"
        if not path.exists():
            checks.append(
                ReleaseCheckItem(
                    name="安全配置",
                    status="FAIL",
                    message=f"未找到安全配置：{path}",
                    recommendation="请提供 configs/ashare_alpha/security.yaml。",
                )
            )
            return
        try:
            payload = load_yaml_config(path)
        except ValueError as exc:
            checks.append(
                ReleaseCheckItem(
                    name="安全配置",
                    status="FAIL",
                    message=f"无法读取 security.yaml：{exc}",
                    recommendation="请修复 YAML 格式。",
                )
            )
            return
        expected = {
            "offline_mode": True,
            "allow_network": False,
            "allow_broker_connections": False,
            "allow_live_trading": False,
        }
        mismatches = [key for key, value in expected.items() if payload.get(key) is not value]
        checks.append(
            ReleaseCheckItem(
                name="安全配置开关",
                status="PASS" if not mismatches else "FAIL",
                message="安全开关符合 MVP 离线边界。" if not mismatches else f"安全开关不符合要求：{', '.join(mismatches)}。",
                recommendation=None if not mismatches else "请保持 offline_mode=true 且网络、券商、实盘交易开关为 false。",
            )
        )

    def _check_forbidden_source_text(self, checks: list[ReleaseCheckItem]) -> None:
        patterns = [
            _phrase("import", "requests"),
            _phrase("import", "httpx"),
            _phrase("import", "tushare"),
            _phrase("import", "akshare"),
            _phrase("from", "a_normal"),
        ]
        matches = self._scan_python_text(patterns)
        checks.append(
            ReleaseCheckItem(
                name="禁用依赖扫描",
                status="PASS" if not matches else "FAIL",
                message="未发现禁用 import。" if not matches else f"发现禁用 import：{'; '.join(matches[:10])}",
                recommendation=None if not matches else "请移除联网 SDK、HTTP 客户端或旧包依赖。",
            )
        )

    def _check_live_order_names(self, checks: list[ReleaseCheckItem]) -> None:
        patterns = [
            "place" + "_order",
            "send" + "_order",
            "live" + "_trade",
            "broker" + "_submit",
            "real" + "_order",
        ]
        matches = self._scan_python_text(patterns)
        checks.append(
            ReleaseCheckItem(
                name="疑似实盘下单函数扫描",
                status="PASS" if not matches else "FAIL",
                message="未发现疑似实盘下单函数名。" if not matches else f"发现疑似实盘下单函数名：{'; '.join(matches[:10])}",
                recommendation=None if not matches else "请移除或重命名任何实盘下单相关实现。",
            )
        )

    def _scan_python_text(self, patterns: list[str]) -> list[str]:
        matches: list[str] = []
        if not self.package_dir.exists():
            return [f"{self.package_dir}: package dir missing"]
        for path in sorted(self.package_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8-sig")
            for pattern in patterns:
                if pattern in text:
                    matches.append(f"{path.relative_to(self.project_root)} contains {pattern}")
        return matches

    def _check_pytest_available(self, checks: list[ReleaseCheckItem]) -> None:
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            checks.append(
                ReleaseCheckItem(
                    name="pytest 可用性",
                    status="FAIL",
                    message="tests 目录不存在。",
                    recommendation="请保留 pytest 测试目录。",
                )
            )
            return
        available = importlib.util.find_spec("pytest") is not None
        checks.append(
            ReleaseCheckItem(
                name="pytest 可用性",
                status="PASS" if available else "WARN",
                message="pytest 可导入。" if available else "pytest 当前环境不可导入。",
                recommendation=None if available else "发布前请在开发环境安装 pytest 并运行完整测试。",
            )
        )

    def _check_ruff_available(self, checks: list[ReleaseCheckItem]) -> None:
        importable = importlib.util.find_spec("ruff") is not None
        executable = shutil.which("ruff") is not None
        available = importable or executable
        checks.append(
            ReleaseCheckItem(
                name="ruff 可用性",
                status="PASS" if available else "WARN",
                message="ruff 可用。" if available else "ruff 当前环境不可导入且不可执行。",
                recommendation=None if available else "发布前请安装 ruff 并运行 ruff check。",
            )
        )

    def _read_version(self) -> str:
        path = self.project_root / "VERSION"
        if not path.exists():
            return "unknown"
        return path.read_text(encoding="utf-8").strip()

    def _check_runtime_version(self, version: str, checks: list[ReleaseCheckItem]) -> None:
        init_path = self.package_dir / "__init__.py"
        if not init_path.exists():
            checks.append(
                ReleaseCheckItem(
                    name="版本一致性",
                    status="FAIL",
                    message=f"未找到 {init_path}。",
                    recommendation="请在 src/ashare_alpha/__init__.py 暴露 __version__。",
                )
            )
            return
        runtime_version = _read_dunder_version(init_path)
        checks.append(
            ReleaseCheckItem(
                name="版本一致性",
                status="PASS" if version == runtime_version else "FAIL",
                message=(
                    f"VERSION 与 __version__ 一致：{version}。"
                    if version == runtime_version
                    else f"VERSION={version}, __version__={runtime_version}。"
                ),
                recommendation=None if version == runtime_version else "请同步 VERSION 与 ashare_alpha.__version__。",
            )
        )

    def _check_document_contains_version(self, file_name: str, version: str, checks: list[ReleaseCheckItem]) -> None:
        path = self.project_root / file_name
        if not path.exists():
            checks.append(
                ReleaseCheckItem(
                    name=f"文档版本：{file_name}",
                    status="FAIL",
                    message=f"{file_name} 不存在，无法检查版本。",
                    recommendation=f"请创建 {file_name} 并写入当前版本。",
                )
            )
            return
        text = path.read_text(encoding="utf-8")
        checks.append(
            ReleaseCheckItem(
                name=f"文档版本：{file_name}",
                status="PASS" if version in text else "FAIL",
                message=f"{file_name} 包含当前版本 {version}。" if version in text else f"{file_name} 未包含当前版本 {version}。",
                recommendation=None if version in text else f"请在 {file_name} 中记录 {version}。",
            )
        )

    def _safety_summary(self) -> dict[str, Any]:
        path = self.config_dir / "security.yaml"
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                payload = load_yaml_config(path)
            except ValueError:
                payload = {}
        return {
            "offline_mode": payload.get("offline_mode"),
            "allow_network": payload.get("allow_network"),
            "allow_broker_connections": payload.get("allow_broker_connections"),
            "allow_live_trading": payload.get("allow_live_trading"),
            "live_trading_supported": False,
            "broker_integration_supported": False,
            "external_api_calls": False,
            "investment_advice": False,
        }


def _phrase(first: str, second: str) -> str:
    return f"{first} {second}"


def _read_dunder_version(path: Path) -> str | None:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    text = path.read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else None
