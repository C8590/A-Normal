from __future__ import annotations

from pathlib import Path

from ashare_alpha.candidates import CandidateRecord, promote_candidate_config


def test_promote_candidate_config_success(tmp_path: Path) -> None:
    config_dir = _config_dir(tmp_path)
    candidate = _candidate(config_dir)

    result = promote_candidate_config(candidate, "test_candidate", tmp_path / "outputs" / "candidate_configs")

    assert result.status == "SUCCESS"
    assert (Path(result.target_config_dir) / "scoring.yaml").exists()
    assert (Path(result.target_config_dir) / "nested" / "rules.json").exists()
    assert not (Path(result.target_config_dir) / "notes.txt").exists()
    assert (Path(result.target_config_dir) / "promotion_manifest.json").exists()


def test_promote_candidate_config_rejects_invalid_name(tmp_path: Path) -> None:
    result = promote_candidate_config(_candidate(_config_dir(tmp_path)), "bad name", tmp_path / "outputs")

    assert result.status == "FAILED"
    assert "promoted_name" in result.message


def test_promote_candidate_config_existing_target_requires_overwrite(tmp_path: Path) -> None:
    config_dir = _config_dir(tmp_path)
    target_root = tmp_path / "outputs"
    assert promote_candidate_config(_candidate(config_dir), "candidate", target_root).status == "SUCCESS"

    failed = promote_candidate_config(_candidate(config_dir), "candidate", target_root)
    overwritten = promote_candidate_config(_candidate(config_dir), "candidate", target_root, allow_overwrite=True)

    assert failed.status == "FAILED"
    assert overwritten.status == "SUCCESS"


def test_promote_candidate_config_rejects_base_config_target(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config_dir = _config_dir(tmp_path)

    result = promote_candidate_config(_candidate(config_dir), "candidate", Path("configs/ashare_alpha"))

    assert result.status == "FAILED"
    assert "configs/ashare_alpha" in result.message


def test_promote_candidate_config_does_not_modify_source(tmp_path: Path) -> None:
    config_dir = _config_dir(tmp_path)
    original = (config_dir / "scoring.yaml").read_text(encoding="utf-8")

    promote_candidate_config(_candidate(config_dir), "candidate", tmp_path / "outputs")

    assert (config_dir / "scoring.yaml").read_text(encoding="utf-8") == original


def _config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    (config_dir / "nested").mkdir(parents=True)
    (config_dir / "scoring.yaml").write_text("thresholds:\n  buy: 80\n", encoding="utf-8")
    (config_dir / "nested" / "rules.json").write_text('{"ok": true}', encoding="utf-8")
    (config_dir / "notes.txt").write_text("skip", encoding="utf-8")
    return config_dir


def _candidate(config_dir: Path | None) -> CandidateRecord:
    return CandidateRecord(
        candidate_id="candidate",
        name="candidate",
        source_type="sweep",
        source_path="sweep_result.json",
        config_dir=str(config_dir) if config_dir else None,
        metrics={"total_return": 0.1},
    )
