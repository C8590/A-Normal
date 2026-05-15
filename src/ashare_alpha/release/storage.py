from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.release.models import ReleaseManifest


def save_release_manifest_json(manifest: ReleaseManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def save_release_checklist_md(manifest: ReleaseManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_release_checklist_md(manifest), encoding="utf-8")


def render_release_checklist_md(manifest: ReleaseManifest) -> str:
    lines = [
        "# Release Checklist",
        "",
        "## 1. 版本信息",
        f"- version: {manifest.version}",
        f"- generated_at: {manifest.generated_at.isoformat()}",
        f"- project_root: {manifest.project_root}",
        f"- python_version: {manifest.python_version}",
        "",
        "## 2. 检查结果",
        f"- checks_passed: {manifest.checks_passed}",
        f"- PASS / WARN / FAIL: {manifest.pass_count} / {manifest.warn_count} / {manifest.fail_count}",
        f"- summary: {manifest.summary}",
        "",
        "| name | status | message | recommendation |",
        "| --- | --- | --- | --- |",
    ]
    for item in manifest.checks:
        lines.append(
            f"| {_cell(item.name)} | {item.status} | {_cell(item.message)} | {_cell(item.recommendation or '-')} |"
        )
    lines.extend(
        [
            "",
            "## 3. 文件检查",
            "| file | exists |",
            "| --- | --- |",
        ]
    )
    for file_name, exists in sorted(manifest.key_files.items()):
        lines.append(f"| `{file_name}` | {exists} |")
    lines.extend(
        [
            "",
            "## 4. 安全检查",
            f"- offline_mode: {manifest.safety_summary.get('offline_mode')}",
            f"- allow_network: {manifest.safety_summary.get('allow_network')}",
            f"- allow_broker_connections: {manifest.safety_summary.get('allow_broker_connections')}",
            f"- allow_live_trading: {manifest.safety_summary.get('allow_live_trading')}",
            "- 不接券商接口。",
            "- 不自动下单。",
            "- 不调用外部 API。",
            "",
            "## 5. 已知限制",
            "- 当前只使用本地 CSV / 离线 fixture。",
            "- 样例数据为测试数据，不代表真实市场。",
            "- 概率模型是基线分箱校准，不保证收益。",
            "- 本系统仅用于研究、回测、信号和报告，不构成投资建议。",
            "",
            "## 6. 发布前建议",
        ]
    )
    for label, command in manifest.key_commands.items():
        lines.append(f"- `{command}` ({label})")
    lines.append("")
    return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
