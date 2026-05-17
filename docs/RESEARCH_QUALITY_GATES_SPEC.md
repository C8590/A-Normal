# Research Quality Gates Spec

## 1. Why

Research outputs can be syntactically successful while still being too weak for promotion. A report may contain warnings, an adjusted comparison may be partial, a backtest may have no trades, or walk-forward validation may have too few successful windows. Research Quality Gates turn those scattered signals into one local quality-control report.

The gates do not add a strategy and do not change default research behavior.

## 2. Decisions

- `PASS`: no blocker or warning issues were found.
- `WARN`: no blocker issues were found, but manual review is required.
- `BLOCK`: at least one blocker issue was found. The artifact should not be used for promotion, release, or effectiveness claims until fixed.

## 3. Supported Artifacts

- `quality_report.json`
- `audit_report.json`
- `security_scan_report.json`
- pipeline `manifest.json`
- backtest `metrics.json`
- `sweep_result.json`
- `walkforward_result.json`
- `candidate_selection.json`
- `adjusted_research_report.json`

## 4. CLI

```bash
python -m ashare_alpha evaluate-research-gates --source outputs/pipelines/pipeline_2026-03-20/manifest.json
python -m ashare_alpha evaluate-research-gates --source outputs/adjusted_research/REPORT_ID/adjusted_research_report.json
python -m ashare_alpha evaluate-research-gates --source outputs/backtests/backtest_2026-01-05_2026-03-20/metrics.json --format json
```

The command writes:

- `research_gate_report.json`
- `research_gate_report.md`
- `research_gate_issues.csv`

Default output directory:

```text
outputs/gates/gates_YYYYMMDD_HHMMSS/
```

`BLOCK` returns a non-zero exit code. `PASS` and `WARN` return zero.

## 5. Rules

Data quality blocks on error-level issues and warns when warning count exceeds the configured threshold.

Leakage audit blocks on error-level issues and warns when warning count exceeds the configured threshold.

Security scan blocks on error-level issues and warns when warning count exceeds the configured threshold.

Pipeline blocks when status is outside `allowed_status`, warns when the allowed universe is below the configured minimum, and warns when high-risk count exceeds the configured maximum.

Backtest warns when filled trades are below the minimum because no-trade backtests cannot validate strategy effectiveness. It blocks on drawdown worse than the configured blocker threshold and warns on low Sharpe.

Sweep blocks when successful variants are below the minimum and warns when failed ratio is too high.

Walk-forward blocks when successful folds are below the minimum or worst drawdown is too severe. It warns on low positive-return ratio, all-no-trade folds, and overfit warnings.

Candidate selection blocks when no candidates exist and warns when too few candidates advance or all are rejected.

Adjusted research blocks on `FAILED`, warns on `PARTIAL`, warns on too many warning items, and warns when factor or backtest comparison coverage is insufficient.

## 6. Candidate And Promote Integration

`select-candidates --gate-report PATH` keeps the old selection behavior but annotates the report. When the gate report is `BLOCK`, the selection report says the input research artifacts did not pass quality gates and are not recommended for advancement.

`promote-candidate-config --gate-report PATH` refuses promotion when the gate report is `BLOCK`. `WARN` allows promotion but prints a warning so a human can review first.

## 7. Dashboard And Experiment Integration

`build-dashboard` scans:

```text
outputs/gates/**/research_gate_report.json
outputs/pipelines/**/gates/research_gate_report.json
```

The dashboard shows the latest research gate decision and warns on `BLOCK` or `WARN`.

Experiment metric extraction records:

- `gate_overall_decision`
- `gate_blocker_count`
- `gate_warning_count`
- `gate_issue_count`

`evaluate-research-gates --record-experiment` records the gate run in the experiment registry.

## 8. Safety Notes

- Gates passing does not guarantee future returns.
- Gates passing does not constitute investment advice.
- Gates do not automatically place orders.
- Gates do not connect to broker interfaces.
- Gates do not call external APIs.
