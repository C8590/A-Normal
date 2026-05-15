from __future__ import annotations

from datetime import date, datetime

from ashare_alpha.pipeline import (
    PipelineManifest,
    PipelineStepResult,
    load_pipeline_manifest,
    render_pipeline_summary_markdown,
    save_pipeline_manifest,
    save_pipeline_summary_md,
)


def test_save_and_load_pipeline_manifest(tmp_path) -> None:
    path = tmp_path / "manifest.json"

    save_pipeline_manifest(_manifest(), path)

    assert path.exists()
    assert load_pipeline_manifest(path).pipeline_date == date(2026, 3, 20)


def test_save_pipeline_summary_markdown(tmp_path) -> None:
    path = tmp_path / "summary.md"

    save_pipeline_summary_md(_manifest(), path)

    text = path.read_text(encoding="utf-8")
    assert "步骤状态" in text
    assert "不构成投资建议" in text


def test_render_pipeline_summary_markdown_contains_status() -> None:
    markdown = render_pipeline_summary_markdown(_manifest())

    assert "SUCCESS" in markdown
    assert "validate_data" in markdown


def _manifest() -> PipelineManifest:
    started = datetime(2026, 3, 20, 9, 0)
    finished = datetime(2026, 3, 20, 9, 0, 1)
    return PipelineManifest(
        pipeline_date=date(2026, 3, 20),
        generated_at=finished,
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        output_dir="outputs/pipelines/pipeline_2026-03-20",
        model_dir=None,
        status="SUCCESS",
        steps=[
            PipelineStepResult(
                name="validate_data",
                status="SUCCESS",
                started_at=started,
                finished_at=finished,
                duration_seconds=1,
                output_paths=[],
                summary={"passed": True},
                error_message=None,
            )
        ],
        total_stocks=12,
        allowed_universe_count=3,
        buy_count=0,
        watch_count=3,
        block_count=9,
        high_risk_count=2,
        market_regime="strong",
    )
