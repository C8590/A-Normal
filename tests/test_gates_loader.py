from __future__ import annotations

from pathlib import Path

from ashare_alpha.gates.loader import ResearchArtifactLoader


def test_loader_infers_supported_artifact_types(tmp_path: Path) -> None:
    loader = ResearchArtifactLoader()
    expected = {
        "quality_report.json": "data_quality",
        "audit_report.json": "leakage_audit",
        "security_scan_report.json": "security",
        "manifest.json": "pipeline",
        "metrics.json": "backtest",
        "sweep_result.json": "sweep",
        "walkforward_result.json": "walkforward",
        "candidate_selection.json": "candidate_selection",
        "adjusted_research_report.json": "adjusted_research",
    }
    for filename, artifact_type in expected.items():
        assert loader.infer_artifact_type(tmp_path / filename) == artifact_type


def test_loader_captures_damaged_json_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "quality_report.json"
    path.write_text("{bad", encoding="utf-8")

    [artifact] = ResearchArtifactLoader().load_many([path])

    assert artifact.artifact_type == "data_quality"
    assert "_loader_error" in artifact.data
