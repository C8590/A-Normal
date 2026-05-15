from __future__ import annotations

from pathlib import Path

import pytest

from ashare_alpha.candidates import CandidateSelector
from candidate_helpers import write_candidate_rules, write_sweep_source, write_wf_source


def test_selector_runs_multiple_sources_and_sorts(tmp_path: Path) -> None:
    rules_path = write_candidate_rules(tmp_path)
    wf_path = write_wf_source(tmp_path, "wf_advance", 0.2, 0.0, 1.0, 0.0, 3, 1)
    sweep_path = write_sweep_source(tmp_path)

    report = CandidateSelector(rules_path, [wf_path, sweep_path]).select()

    assert report.total_candidates == 3
    assert report.scores == sorted(report.scores, key=lambda score: score.total_score, reverse=True)
    assert report.advance_count == 1
    assert report.review_count == 1
    assert report.reject_count == 1


def test_selector_no_candidates_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No candidate"):
        CandidateSelector(write_candidate_rules(tmp_path), [tmp_path]).select()
