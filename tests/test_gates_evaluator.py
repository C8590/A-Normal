from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.gates import DEFAULT_GATE_CONFIG_PATH, ResearchGateEvaluator, load_research_quality_gate_config


def _evaluate(path: Path):
    return ResearchGateEvaluator(
        gate_config=load_research_quality_gate_config(DEFAULT_GATE_CONFIG_PATH),
        artifact_paths=[path],
        gate_config_path=DEFAULT_GATE_CONFIG_PATH,
    ).evaluate()


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_quality_report_error_blocks(tmp_path: Path) -> None:
    report = _evaluate(
        _write_json(
            tmp_path / "quality_report.json",
            {"passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0},
        )
    )

    assert report.overall_decision == "BLOCK"
    assert report.blocker_count == 1


def test_security_scan_error_blocks(tmp_path: Path) -> None:
    report = _evaluate(
        _write_json(
            tmp_path / "security_scan_report.json",
            {"passed": False, "total_issues": 1, "error_count": 1, "warning_count": 0, "info_count": 0},
        )
    )

    assert report.overall_decision == "BLOCK"


def test_backtest_no_trade_warns(tmp_path: Path) -> None:
    report = _evaluate(
        _write_json(
            tmp_path / "metrics.json",
            {"filled_trade_count": 0, "trade_count": 0, "max_drawdown": 0, "sharpe": 0},
        )
    )

    assert report.overall_decision == "WARN"
    assert any(issue.issue_type == "backtest_low_trade_count" for issue in report.issues)


def test_walkforward_low_success_count_blocks(tmp_path: Path) -> None:
    report = _evaluate(
        _write_json(
            tmp_path / "walkforward_result.json",
            {
                "success_count": 1,
                "fold_count": 1,
                "stability_metrics": {"positive_return_ratio": 1.0, "worst_max_drawdown": 0},
                "overfit_warnings": [],
                "folds": [],
            },
        )
    )

    assert report.overall_decision == "BLOCK"
    assert any(issue.issue_type == "walkforward_low_success_count" for issue in report.issues)


def test_adjusted_research_partial_warns(tmp_path: Path) -> None:
    report = _evaluate(
        _write_json(
            tmp_path / "adjusted_research_report.json",
            {
                "status": "PARTIAL",
                "warning_items": ["sample"],
                "factor_comparisons": [{}],
                "backtest_comparisons": [{}],
            },
        )
    )

    assert report.overall_decision == "WARN"
    assert any(issue.issue_type == "adjusted_research_partial" for issue in report.issues)
