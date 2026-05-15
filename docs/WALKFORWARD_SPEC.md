# Walk-forward Spec

Walk-forward validation splits a historical period into multiple out-of-sample test windows and runs the same research setup repeatedly. It helps reveal whether a backtest result is stable across time or concentrated in one lucky window.

It is an offline research validation tool. It does not constitute investment advice, does not guarantee future returns, and does not automatically place orders.

## 1. Why Walk-forward

A single backtest can hide instability. A sweep can compare many parameter variants, but it still may be evaluated over one broad period. Walk-forward validation asks a different question: does the same setup behave consistently across several later windows?

- Single backtest: one configuration, one period.
- Sweep: many configurations, one command run per variant.
- Walk-forward: one setup or one sweep, many time windows.

## 2. YAML Structure

Example:

```yaml
name: sample_backtest_walkforward
description: "MVP 样例数据的滚动样本外回测"
command: run-backtest
data_dir: data/sample/ashare_alpha
base_config_dir: configs/ashare_alpha
output_root_dir: outputs/walkforward
experiment_registry_dir: outputs/experiments
start_date: "2026-01-05"
end_date: "2026-03-20"
train_window_days: null
test_window_days: 21
step_days: 14
min_test_trading_days: 5
common_args: {}
tags:
  - walkforward
  - mvp
notes: "用于验证回测流程稳定性，不代表投资建议"
```

Supported `command` values:

- `run-backtest`
- `run-sweep`

When `command: run-sweep`, `sweep_spec` is required. For each fold, Walk-forward creates a folded copy of that sweep spec and overrides `common_args.start` and `common_args.end` with the fold test window.

## 3. Fold Generation

The first version uses calendar days rather than a full exchange calendar:

- `test_start` begins at `start_date`
- `test_end = test_start + test_window_days - 1`
- next `test_start += step_days`
- windows whose `test_end` exceeds `end_date` are not generated
- if `train_window_days` is set, `train_end` is the day before `test_start`

`min_test_trading_days` is checked against local CSV trading days. A fold with too few trading days is marked `SKIPPED`.

## 4. CLI

Run validation:

```bash
python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml
python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml --format json
```

Show a completed result:

```bash
python -m ashare_alpha show-walkforward --path outputs/walkforward/WF_ID/walkforward_result.json
python -m ashare_alpha show-walkforward --path outputs/walkforward/WF_ID/walkforward_result.json --format json
```

If every fold fails, `run-walkforward` returns non-zero. Partial failures return zero and are called out in the text output.

## 5. Output Layout

```text
outputs/walkforward/WF_ID/
  walkforward_result.json
  walkforward_summary.md
  fold_metrics.csv
  folds/
    fold_001/
      metrics.json
      trades.csv
      daily_equity.csv
      summary.md
```

For `run-sweep` folds, each fold contains the folded sweep spec plus that fold's sweep output directory.

## 6. Stability Metrics

`stability_metrics` may include:

- `fold_count`
- `success_fold_count`
- `positive_return_fold_count`
- `positive_return_ratio`
- `mean_total_return`
- `median_total_return`
- `std_total_return`
- `min_total_return`
- `max_total_return`
- `worst_fold_index`
- `mean_max_drawdown`
- `worst_max_drawdown`

Missing metrics remain `null` or blank in CSV outputs.

## 7. Overfit Warnings

`overfit_warnings` are simple guardrails, not proofs:

- too few successful folds
- fewer than half the folds are positive
- return volatility is much larger than mean return
- a fold has a large drawdown
- all folds have zero trades
- some folds lack analyzable metrics

These warnings are intended to make fragile results harder to overlook.

## 8. Experiment Registry

Each successful or partial fold records an experiment in `experiment_registry_dir`. Fold tags include `walkforward`, the walk-forward name, and `fold_XXX`. Failed folds are kept in the walk-forward result with an error message.
