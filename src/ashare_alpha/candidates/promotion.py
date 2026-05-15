from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from ashare_alpha.candidates.models import CandidatePromotionResult, CandidateRecord


class ConfigPromoter:
    def promote_candidate_config(
        self,
        candidate: CandidateRecord,
        promoted_name: str,
        target_root: Path,
        allow_overwrite: bool = False,
    ) -> CandidatePromotionResult:
        return promote_candidate_config(candidate, promoted_name, target_root, allow_overwrite)


def promote_candidate_config(
    candidate: CandidateRecord,
    promoted_name: str,
    target_root: Path,
    allow_overwrite: bool = False,
) -> CandidatePromotionResult:
    if not candidate.config_dir:
        return _failed(candidate, promoted_name, "", Path(target_root) / promoted_name, "候选没有 config_dir，无法复制配置快照。")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", promoted_name):
        return _failed(candidate, promoted_name, candidate.config_dir, Path(target_root) / promoted_name, "promoted_name 只能包含字母、数字、下划线和短横线。")

    source_config_dir = Path(candidate.config_dir)
    target_root = Path(target_root)
    target_config_dir = target_root / promoted_name
    if not source_config_dir.exists() or not source_config_dir.is_dir():
        return _failed(candidate, promoted_name, str(source_config_dir), target_config_dir, f"源配置目录不存在: {source_config_dir}")
    if _is_base_config_target(target_root):
        return _failed(candidate, promoted_name, str(source_config_dir), target_config_dir, "不允许将候选配置复制到 configs/ashare_alpha。")
    if target_config_dir.exists() and not allow_overwrite:
        return _failed(candidate, promoted_name, str(source_config_dir), target_config_dir, f"目标目录已存在: {target_config_dir}")

    if target_config_dir.exists() and allow_overwrite:
        shutil.rmtree(target_config_dir)
    target_config_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for source_file in sorted(source_config_dir.rglob("*")):
        if not source_file.is_file() or source_file.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        relative_path = source_file.relative_to(source_config_dir)
        if any(part in {"outputs", "data", "__pycache__"} for part in relative_path.parts):
            continue
        target_file = target_config_dir / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied_files.append(str(relative_path))

    result = CandidatePromotionResult(
        candidate_id=candidate.candidate_id,
        promoted_name=promoted_name,
        source_config_dir=str(source_config_dir),
        target_config_dir=str(target_config_dir),
        copied_files=copied_files,
        status="SUCCESS",
        message="配置快照已复制，仅用于下一轮研究验证，不会修改 base config，也不会触发实盘操作。",
    )
    manifest = {
        **result.model_dump(mode="json"),
        "generated_at": datetime.now().isoformat(),
        "candidate": candidate.model_dump(mode="json"),
    }
    (target_config_dir / "promotion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _failed(
    candidate: CandidateRecord,
    promoted_name: str,
    source_config_dir: str,
    target_config_dir: Path,
    message: str,
) -> CandidatePromotionResult:
    return CandidatePromotionResult(
        candidate_id=candidate.candidate_id,
        promoted_name=promoted_name,
        source_config_dir=source_config_dir,
        target_config_dir=str(target_config_dir),
        copied_files=[],
        status="FAILED",
        message=message,
    )


def _is_base_config_target(target_root: Path) -> bool:
    normalized = Path(target_root).resolve()
    forbidden = Path("configs/ashare_alpha").resolve()
    return normalized == forbidden or forbidden in normalized.parents
