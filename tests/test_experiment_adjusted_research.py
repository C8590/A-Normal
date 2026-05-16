from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.experiments import extract_metrics_from_output


def test_experiment_extracts_adjusted_research_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted_research"
    output_dir.mkdir()
    (output_dir / "adjusted_research_report.json").write_text(
        json.dumps(
            {
                "factor_comparisons": [{}, {}],
                "backtest_comparisons": [
                    {
                        "left_price_source": "raw",
                        "right_price_source": "qfq",
                        "total_return_diff": 0.1,
                        "sharpe_diff": 0.2,
                    },
                    {
                        "left_price_source": "raw",
                        "right_price_source": "hfq",
                        "total_return_diff": 0.3,
                        "sharpe_diff": 0.4,
                    },
                ],
                "warning_items": ["INFO: sample"],
            }
        ),
        encoding="utf-8",
    )

    metrics = extract_metrics_from_output(output_dir, "adjusted-research-report")
    by_name = {metric.name: metric.value for metric in metrics}

    assert by_name["factor_comparison_count"] == 2
    assert by_name["backtest_comparison_count"] == 2
    assert by_name["warning_count"] == 1
    assert by_name["raw_qfq_total_return_diff"] == 0.1
    assert by_name["raw_hfq_sharpe_diff"] == 0.4
