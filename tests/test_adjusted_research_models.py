from __future__ import annotations

from datetime import date, datetime

from ashare_alpha.adjusted_research import AdjustedResearchReport, AdjustedResearchStepResult


def test_adjusted_research_report_serializes() -> None:
    report = AdjustedResearchReport(
        report_id="adjusted_research_test",
        generated_at=datetime(2026, 5, 16, 12, 0, 0),
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        target_date=date(2026, 3, 20),
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        status="SUCCESS",
        steps=[
            AdjustedResearchStepResult(
                name="compute-factors raw",
                status="SUCCESS",
                started_at=datetime(2026, 5, 16, 12, 0, 0),
                finished_at=datetime(2026, 5, 16, 12, 0, 1),
                duration_seconds=1.0,
            )
        ],
        output_dir="outputs/adjusted_research/x",
        summary="ok",
    )

    payload = report.model_dump(mode="json")

    assert payload["target_date"] == "2026-03-20"
    assert payload["steps"][0]["status"] == "SUCCESS"
