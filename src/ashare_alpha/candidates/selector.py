from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha.candidates.loader import (
    load_candidate_from_experiment,
    load_candidates_from_sweep,
    load_candidates_from_walkforward,
)
from ashare_alpha.candidates.models import CandidateRecord, CandidateSelectionReport, CandidateSource
from ashare_alpha.candidates.scoring import CandidateScorer, load_candidate_rules


class CandidateSelector:
    def __init__(self, rules_path: Path, sources: list[Path]) -> None:
        self.rules_path = Path(rules_path)
        self.sources = [Path(source) for source in sources]

    def select(self) -> CandidateSelectionReport:
        rules = load_candidate_rules(self.rules_path)
        candidates: list[CandidateRecord] = []
        source_records: list[CandidateSource] = []
        for source_path in self.sources:
            loaded_source, loaded_candidates = self._load_source(source_path)
            source_records.append(loaded_source)
            candidates.extend(loaded_candidates)
        if not candidates:
            raise ValueError("No candidate records were loaded from the provided sources.")

        scorer = CandidateScorer(rules)
        scores = sorted((scorer.score(candidate) for candidate in candidates), key=lambda item: item.total_score, reverse=True)
        candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
        ordered_candidates = [candidate_by_id[score.candidate_id] for score in scores if score.candidate_id in candidate_by_id]
        summary = _build_summary(scores)
        return CandidateSelectionReport(
            selection_id=f"selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            rules_path=str(self.rules_path),
            sources=source_records,
            total_candidates=len(scores),
            advance_count=sum(1 for score in scores if score.recommendation == "ADVANCE"),
            review_count=sum(1 for score in scores if score.recommendation == "REVIEW"),
            reject_count=sum(1 for score in scores if score.recommendation == "REJECT"),
            scores=scores,
            summary=summary,
            candidates=ordered_candidates,
        )

    def _load_source(self, path: Path) -> tuple[CandidateSource, list[CandidateRecord]]:
        if not path.exists():
            raise ValueError(f"candidate source does not exist: {path}")
        if path.is_dir():
            candidates = [load_candidate_from_experiment(record_path) for record_path in sorted(path.glob("*.json"))]
            return CandidateSource(source_type="experiment", path=str(path), source_id=path.name), candidates
        source_type = _detect_source_type(path)
        if source_type == "sweep":
            candidates = load_candidates_from_sweep(path)
        elif source_type == "walkforward":
            candidates = load_candidates_from_walkforward(path)
        else:
            candidates = [load_candidate_from_experiment(path)]
        source_id = _source_id(path, source_type)
        return CandidateSource(source_type=source_type, path=str(path), source_id=source_id), candidates


def _detect_source_type(path: Path) -> str:
    if path.name == "sweep_result.json":
        return "sweep"
    if path.name == "walkforward_result.json":
        return "walkforward"
    payload = _read_json(path)
    if isinstance(payload, dict):
        if "sweep_id" in payload and "runs" in payload:
            return "sweep"
        if "walkforward_id" in payload and "folds" in payload:
            return "walkforward"
        if "experiment_id" in payload and "metrics" in payload:
            return "experiment"
    raise ValueError(f"Cannot detect candidate source type: {path}")


def _source_id(path: Path, source_type: str) -> str | None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    key = {"sweep": "sweep_id", "walkforward": "walkforward_id", "experiment": "experiment_id"}[source_type]
    value = payload.get(key)
    return str(value) if value else None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON candidate source: {path}") from exc


def _build_summary(scores) -> str:
    total = len(scores)
    advance_count = sum(1 for score in scores if score.recommendation == "ADVANCE")
    review_count = sum(1 for score in scores if score.recommendation == "REVIEW")
    reject_count = sum(1 for score in scores if score.recommendation == "REJECT")
    top = scores[:3]
    top_text = "；".join(f"{score.name}({score.total_score:.2f}, {score.recommendation})" for score in top) or "无"
    return (
        f"本次共评估 {total} 个研究候选，其中 ADVANCE {advance_count} 个、REVIEW {review_count} 个、"
        f"REJECT {reject_count} 个。排名靠前候选：{top_text}。"
        "该结果只是研究筛选，不代表未来收益，不构成投资建议，不保证未来收益，也不会自动下单。"
    )
