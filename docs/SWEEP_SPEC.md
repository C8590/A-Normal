# Sweep Runner Spec

Sweep Runner is a local, offline batch experiment runner. It copies a base `config_dir`, applies small YAML overrides for each variant, runs one supported research command, records each variant in the Experiment Registry, and writes a consolidated metrics table.

It is only for research comparison. It does not constitute investment advice, does not guarantee future returns, and does not automatically place orders.

## 1. Sweep YAML

Example:

```yaml
sweep_name: sample_pipeline_thresholds
description: "比较不同 BUY 阈值对每日信号数量的影响"
command: run-pipeline
base_config_dir: configs/ashare_alpha
data_dir: data/sample/ashare_alpha
output_root_dir: outputs/sweeps
experiment_registry_dir: outputs/experiments
common_args:
  date: "2026-03-20"
variants:
  - name: buy_85
    config_overrides:
      scoring.yaml:
        thresholds.buy: 85
    tags: ["sweep", "threshold"]
```

Supported `command` values:

- `run-pipeline`
- `run-backtest`
- `train-probability-model`

`common_args` are shared by all variants. `variant.command_args` can override or add command-specific values such as `data_dir`.

## 2. Config Overrides

`config_overrides` uses two levels:

- first level: existing YAML file name under the copied `config_dir`
- second level: dot path inside that YAML file

```yaml
config_overrides:
  scoring.yaml:
    thresholds.buy: 85
    position_sizing.strong_buy_score: 92
  backtest.yaml:
    max_positions: 1
```

The dot path must already exist. Missing files and misspelled paths fail the variant so accidental new parameters are not silently created. After overrides are written, `load_project_config` validates the full project config schema.

## 3. Safety Limits

Sweeps cannot loosen the offline safety boundary:

- cannot set `security.yaml: allow_network` to `true`
- cannot set `security.yaml: allow_broker_connections` to `true`
- cannot set `security.yaml: allow_live_trading` to `true`
- cannot set `security.yaml: offline_mode` to `false`
- cannot write plaintext secret-like keys containing `token`, `api_key`, `secret`, or `password`

Secret-like override values are allowed only when the value is `null` or an environment variable name starting with `ASHARE_ALPHA_`.

## 4. CLI

Run a sweep:

```bash
python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml
python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml --format json
```

Show a completed sweep:

```bash
python -m ashare_alpha show-sweep --path outputs/sweeps/SWEEP_ID/sweep_result.json
python -m ashare_alpha show-sweep --path outputs/sweeps/SWEEP_ID/sweep_result.json --format json
```

If all variants fail, `run-sweep` returns non-zero. If only some variants fail, it returns zero and reports partial failure in the text output.

## 5. Output Layout

```text
outputs/sweeps/SWEEP_ID/
  sweep_result.json
  sweep_summary.md
  metrics_table.csv
  variants/
    VARIANT_NAME/
      config/
      config_changes.json
      config_changes.md
      output/
```

Each successful or partial variant is automatically recorded in `experiment_registry_dir`. Failed variants are also recorded when enough local output context exists.

## 6. Metrics Table

`metrics_table.csv` includes base columns:

- `variant_name`
- `status`
- `experiment_id`
- `output_dir`
- `duration_seconds`

Command-specific columns:

- `run-pipeline`: `buy_count`, `watch_count`, `block_count`, `high_risk_count`, `allowed_universe_count`, `probability_predictable_count`
- `run-backtest`: `total_return`, `max_drawdown`, `sharpe`, `trade_count`, `filled_trade_count`, `rejected_trade_count`
- `train-probability-model`: `auc_5d`, `brier_score_5d`, `actual_win_rate_5d`

Missing metrics are left blank.
