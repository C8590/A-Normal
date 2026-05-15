# Candidate Selection Spec

Candidate Selection evaluates completed offline research results from sweeps, walk-forward validation, and experiment records. It ranks candidate configurations for the next research round without changing strategy logic, backtest logic, probability-model logic, or base configuration files.

The feature is a research filter only. It does not constitute investment advice, does not guarantee future returns, does not connect to brokers, and does not place orders.

## 1. Why Candidate Selection Exists

Sweep and walk-forward runs can produce many result directories. Candidate Selection provides a consistent way to compare those results using return, drawdown, stability, trade activity, and warning signals. The output is a ranked candidate report with a conservative recommendation:

- `ADVANCE`: research candidate suggested for the next validation round.
- `REVIEW`: candidate requires manual review before any further research.
- `REJECT`: candidate is not suggested for promotion.

These labels are research workflow labels only.

## 2. select-candidates

Run candidate selection against one or more result files:

```bash
python -m ashare_alpha select-candidates \
  --source outputs/walkforward/WF_ID/walkforward_result.json

python -m ashare_alpha select-candidates \
  --source outputs/sweeps/SWEEP_ID/sweep_result.json \
  --source outputs/walkforward/WF_ID/walkforward_result.json \
  --format json
```

Default rules are loaded from:

```text
configs/ashare_alpha/candidates/default_candidate_rules.yaml
```

Outputs are written under `outputs/candidates/selection_YYYYMMDD_HHMMSS/` unless `--output-dir` is provided:

- `candidate_selection.json`
- `candidate_selection.md`
- `candidate_scores.csv`

## 3. CandidateRules

`CandidateRules` contains:

- `selection_name`: human-readable rule-set name.
- `weights`: weights for return, drawdown, stability, trade activity, and warning penalty scores. The sum must be close to 1.
- `thresholds`: basic filters for fold count, positive-return ratio, worst drawdown, trade count, and warning count.
- `scoring`: caps and floors used to map metrics to 0-100 scores.
- `promotion`: promotion safety settings. `allow_auto_promote` defaults to `false`.

Promotion does not automatically overwrite or modify `configs/ashare_alpha`.

## 4. Scores

- `return_score`: uses `mean_total_return`, `total_return`, or `annualized_return`.
- `drawdown_score`: uses `worst_max_drawdown`, `max_drawdown`, or `mean_max_drawdown`; drawdown closer to zero scores higher.
- `stability_score`: uses `positive_return_ratio`, `std_total_return`, and `success_fold_count`.
- `trade_activity_score`: treats zero-trade results cautiously. Zero trades are allowed but receive a warning because they cannot validate trading effectiveness.
- `warning_penalty_score`: subtracts risk points for warnings, especially overfit-related warnings such as too few windows, most windows not positive, unstable returns, or large-drawdown windows.

The final score is clamped to 0-100.

## 5. Basic Filters

Basic filters fail when:

- a walk-forward candidate has too few successful folds,
- `positive_return_ratio` is below the configured threshold,
- `worst_max_drawdown` is worse than the configured threshold,
- warning count exceeds the configured threshold,
- metrics are empty.

Filter reasons are written in Chinese in the report.

## 6. promote-candidate-config

Promotion copies a candidate's config snapshot to a research output directory:

```bash
python -m ashare_alpha promote-candidate-config \
  --selection outputs/candidates/selection_ID/candidate_selection.json \
  --candidate-id CANDIDATE_ID \
  --promoted-name test_candidate
```

The default target is:

```text
outputs/candidate_configs/test_candidate/
```

Only `.yaml`, `.yml`, and `.json` files are copied. `outputs`, `data`, and `__pycache__` are not copied. A `promotion_manifest.json` is generated in the target directory.

The command refuses to target `configs/ashare_alpha`; it does not modify base config, does not run a strategy, and does not trigger any trading action.

## 7. Safety Boundary

Candidate Selection and promotion are offline research workflow tools. They do not fetch data, scrape websites, call external APIs, connect to brokers, submit orders, guarantee future returns, or automatically change the strategy used by existing commands.
