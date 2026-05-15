from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ashare_alpha.security.models import SecurityScanIssue, SecurityScanReport


SENSITIVE_KEY_PARTS = (
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_key",
    "refresh_token",
)
SKIPPED_DIRS = {".git", "outputs", "data", ".pytest_cache", ".ruff_cache", "__pycache__"}
SCAN_EXTENSIONS = {".yaml", ".yml", ".json"}


class ConfigSecurityScanner:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = Path(config_dir)

    def scan(self) -> SecurityScanReport:
        issues: list[SecurityScanIssue] = []
        if not self.config_dir.exists():
            issues.append(
                _issue(
                    "error",
                    str(self.config_dir),
                    None,
                    "missing_config_dir",
                    f"配置目录不存在：{self.config_dir}",
                    "请提供有效的配置目录。",
                )
            )
            return _report(self.config_dir, issues)
        for path in self._iter_scan_files():
            self._scan_file(path, issues)
        return _report(self.config_dir, issues)

    def _iter_scan_files(self) -> list[Path]:
        if self.config_dir.is_file():
            return [self.config_dir] if self.config_dir.suffix.lower() in SCAN_EXTENSIONS else []
        paths: list[Path] = []
        for path in self.config_dir.rglob("*"):
            if any(part in SKIPPED_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in SCAN_EXTENSIONS:
                paths.append(path)
        return sorted(paths)

    def _scan_file(self, path: Path, issues: list[SecurityScanIssue]) -> None:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            issues.append(
                _issue(
                    "warning",
                    str(path),
                    None,
                    "scan_read_error",
                    f"无法解析配置文件：{exc}",
                    "请确认 YAML/JSON 文件格式正确。",
                )
            )
            return
        self._scan_node(payload, path, [], issues)

    def _scan_node(self, node: Any, file_path: Path, key_path: list[str], issues: list[SecurityScanIssue]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = [*key_path, str(key)]
                self._scan_key_value(file_path, current_path, value, issues)
                self._scan_node(value, file_path, current_path, issues)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                self._scan_node(item, file_path, [*key_path, str(index)], issues)

    def _scan_key_value(
        self,
        file_path: Path,
        key_path: list[str],
        value: Any,
        issues: list[SecurityScanIssue],
    ) -> None:
        key = key_path[-1].lower()
        dotted = ".".join(key_path)
        if key == "allow_live_trading" and value is True:
            issues.append(
                _issue(
                    "error",
                    str(file_path),
                    dotted,
                    "live_trading_enabled",
                    "配置中启用了 allow_live_trading=true。",
                    "MVP 必须保持实盘交易关闭。",
                )
            )
        if key == "allow_broker_connections" and value is True:
            issues.append(
                _issue(
                    "error",
                    str(file_path),
                    dotted,
                    "broker_connection_enabled",
                    "配置中启用了 allow_broker_connections=true。",
                    "MVP 必须保持券商连接关闭。",
                )
            )
        if not _is_sensitive_key(key):
            return
        if value is None or value == "":
            return
        if not isinstance(value, str):
            return
        if _is_safe_env_var(value):
            return
        if len(value) > 12:
            issues.append(
                _issue(
                    "error",
                    str(file_path),
                    dotted,
                    "plaintext_secret",
                    "配置文件中疑似包含明文密钥。",
                    "不要把 API key/token 写入配置文件，请改用 ASHARE_ALPHA_ 前缀的环境变量名。",
                )
            )


def _is_sensitive_key(key: str) -> bool:
    return any(part in key for part in SENSITIVE_KEY_PARTS)


def _is_safe_env_var(value: str) -> bool:
    return value.startswith("ASHARE_ALPHA_") and value.replace("_", "").isalnum() and value.upper() == value


def _issue(
    severity: str,
    file_path: str,
    key_path: str | None,
    issue_type: str,
    message: str,
    recommendation: str,
) -> SecurityScanIssue:
    return SecurityScanIssue(
        severity=severity,
        file_path=file_path,
        key_path=key_path,
        issue_type=issue_type,
        message=message,
        recommendation=recommendation,
    )


def _report(config_dir: Path, issues: list[SecurityScanIssue]) -> SecurityScanReport:
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    passed = error_count == 0
    return SecurityScanReport(
        generated_at=datetime.now(),
        config_dir=str(config_dir),
        total_issues=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        passed=passed,
        issues=issues,
        summary=(
            f"安全配置扫描{'通过' if passed else '未通过'}："
            f"error={error_count}, warning={warning_count}, info={info_count}。"
        ),
    )
