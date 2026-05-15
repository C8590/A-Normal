from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.candidates.models import CandidatePromotionResult, CandidateSelectionReport


def save_candidate_selection_report_json(report: CandidateSelectionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_candidate_selection_report_json(path: Path) -> CandidateSelectionReport:
    return CandidateSelectionReport.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_candidate_selection_report_md(report: CandidateSelectionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_md(report), encoding="utf-8")


def save_candidate_scores_csv(report: CandidateSelectionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "candidate_id",
        "name",
        "source_type",
        "total_score",
        "recommendation",
        "return_score",
        "drawdown_score",
        "stability_score",
        "trade_activity_score",
        "warning_penalty_score",
        "passed_basic_filters",
        "filter_reasons",
    ]
    candidate_source = {candidate.candidate_id: candidate.source_type for candidate in report.candidates}
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for rank, score in enumerate(report.scores, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "candidate_id": score.candidate_id,
                    "name": score.name,
                    "source_type": candidate_source.get(score.candidate_id, ""),
                    "total_score": score.total_score,
                    "recommendation": score.recommendation,
                    "return_score": score.return_score,
                    "drawdown_score": score.drawdown_score,
                    "stability_score": score.stability_score,
                    "trade_activity_score": score.trade_activity_score,
                    "warning_penalty_score": score.warning_penalty_score,
                    "passed_basic_filters": score.passed_basic_filters,
                    "filter_reasons": "；".join(score.filter_reasons),
                }
            )


def save_promotion_result_json(result: CandidatePromotionResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def _render_md(report: CandidateSelectionReport) -> str:
    candidate_source = {candidate.candidate_id: candidate.source_type for candidate in report.candidates}
    lines = [
        "# 候选配置评估报告",
        "",
        "## 1. 基本信息",
        f"- selection_id: {report.selection_id}",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- rules_path: {report.rules_path}",
        f"- sources: {', '.join(source.path for source in report.sources) if report.sources else '-'}",
        f"- total_candidates: {report.total_candidates}",
        "",
        "## 2. 候选排名",
        "| rank | candidate_id | name | source_type | total_score | recommendation | return_score | drawdown_score | stability_score | warning_penalty_score | filter_reasons |",
        "| ---: | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for rank, score in enumerate(report.scores, start=1):
        lines.append(
            "| "
            f"{rank} | "
            f"{_escape(score.candidate_id)} | "
            f"{_escape(score.name)} | "
            f"{candidate_source.get(score.candidate_id, '-')} | "
            f"{score.total_score:.2f} | "
            f"{score.recommendation} | "
            f"{score.return_score:.2f} | "
            f"{score.drawdown_score:.2f} | "
            f"{score.stability_score:.2f} | "
            f"{score.warning_penalty_score:.2f} | "
            f"{_escape('；'.join(score.filter_reasons) or '-')} |"
        )
    lines.extend(
        [
            "",
            "## 3. ADVANCE 候选",
            *_candidate_lines(report, "ADVANCE", "建议进入下一轮验证"),
            "",
            "## 4. REVIEW 候选",
            *_candidate_lines(report, "REVIEW", "需要人工复核"),
            "",
            "## 5. REJECT 候选",
            *_candidate_lines(report, "REJECT", "不建议晋级"),
            "",
            "## 6. 说明",
            "- 仅用于研究筛选。",
            "- 不构成投资建议。",
            "- 不保证未来收益。",
            "- 不自动下单。",
            "",
            report.summary,
            "",
        ]
    )
    return "\n".join(lines)


def _candidate_lines(report: CandidateSelectionReport, recommendation: str, label: str) -> list[str]:
    rows = [score for score in report.scores if score.recommendation == recommendation]
    if not rows:
        return ["- 无"]
    return [
        f"- {score.name}: {label}，score={score.total_score:.2f}，原因={'; '.join(score.filter_reasons) or '通过基础过滤'}"
        for score in rows
    ]


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
