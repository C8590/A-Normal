# Experiment Registry Spec

Experiment Registry records the provenance of research runs so a pipeline, backtest, or probability-training result can be traced back to its command, data directory, data version, config hash, output files, and extracted metrics.

The registry is an offline research tool. It does not rerun strategies, fetch data, connect to brokers, place orders, or provide investment advice.

## 1. Why It Exists

Research outputs are easy to lose context for: a backtest metric may depend on a specific data import, YAML config set, and command flag combination. Experiment records make that context explicit and comparable.

Default registry directory:

```text
outputs/experiments/
  index.json
  records/
  comparisons/
```

## 2. Experiment ID

`experiment_id` is generated as:

```text
exp_YYYYMMDD_HHMMSS_<short_hash>
```

`short_hash` is the first 8 characters of a SHA-256 hash over command, command args, config hash, data version, and creation time.

## 3. Config Hash

`config_hash` is a SHA-256 digest over sorted `.yaml`, `.yml`, and `.json` files under `config_dir`.

Rules:

- files are scanned recursively and sorted by relative path
- `__pycache__`, output directories, and temporary files are skipped
- environment variable values are never read
- `security.yaml` `api_key_env_var` values are hashed only as environment variable names, not secret values

## 4. Data Version Inference

The recorder infers data provenance from `data_dir`:

- `data/imports/{source}/{version}` -> `data_source={source}`, `data_version={version}`
- `data/materialized/{source}/{version}` -> `data_source={source}`, `data_version={version}`
- `data/sample/ashare_alpha` -> `data_source=local_csv`, `data_version=sample`
- otherwise both fields are `null`

## 5. Manual Recording

Record an already completed run:

```bash
python -m ashare_alpha record-experiment \
  --command run-pipeline \
  --output-dir outputs/pipelines/pipeline_2026-03-20 \
  --data-dir data/sample/ashare_alpha \
  --tag mvp \
  --notes "MVP sample pipeline"
```

The command discovers artifacts up to two directory levels deep and extracts recognized metrics from existing output files.

## 6. Listing

```bash
python -m ashare_alpha list-experiments
python -m ashare_alpha list-experiments --format json
python -m ashare_alpha list-experiments --command run-pipeline
python -m ashare_alpha list-experiments --tag mvp
```

## 7. Showing One Experiment

```bash
python -m ashare_alpha show-experiment --id EXP_ID
python -m ashare_alpha show-experiment --id EXP_ID --format json
```

## 8. Comparing Experiments

```bash
python -m ashare_alpha compare-experiments \
  --baseline EXP_A \
  --target EXP_B
```

Outputs:

- `outputs/experiments/comparisons/compare_EXP_A_EXP_B.json`
- `outputs/experiments/comparisons/compare_EXP_A_EXP_B.md`

The comparison aligns metrics by name. Numeric metrics include baseline value, target value, absolute diff, and percentage diff when the baseline is nonzero. Non-numeric metrics show baseline and target values only.

## 9. Pipeline Integration

`run-pipeline` can record experiments when explicitly enabled:

```bash
python -m ashare_alpha run-pipeline \
  --date 2026-03-20 \
  --record-experiment \
  --experiment-tag mvp \
  --experiment-notes "sample pipeline"
```

This does not change default pipeline behavior. If the flag is omitted, no experiment record is created.

## 10. Backtest Integration

`run-backtest` can also record experiments:

```bash
python -m ashare_alpha run-backtest \
  --start 2026-01-05 \
  --end 2026-03-20 \
  --record-experiment \
  --experiment-tag backtest
```

## 11. Risk Boundary

Experiment comparison is a historical research aid only. It does not imply future performance, does not guarantee returns, and does not constitute investment advice. The system remains offline, does not connect to broker APIs, and does not submit live orders.
