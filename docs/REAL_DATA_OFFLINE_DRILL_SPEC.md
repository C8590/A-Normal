# v0.3 Real Data Offline Drill Spec

`run-realdata-offline-drill` is the v0.3 rehearsal workflow for future real data ingestion. It remains fully offline: it uses local fixtures and cache/materialization/import steps only. It does not call external APIs, scrape websites, connect to brokers, or place orders.

## Goal

The drill connects the existing offline ingestion and research chain into one reproducible command:

```text
offline fixture/cache
 -> cache-source-fixture
 -> materialize-cache
 -> materialize-source
 -> import-data
 -> validate-data
 -> quality-report
 -> audit-leakage
 -> run-pipeline
 -> build-frontend
 -> build-dashboard
 -> record-experiment
```

## Specs

Example specs live under `configs/ashare_alpha/realdata/`:

- `tushare_like_offline_drill.yaml`
- `akshare_like_offline_drill.yaml`

Fields:

```yaml
drill_name: tushare_like_offline_drill
source_profile: configs/ashare_alpha/source_profiles/tushare_like_offline.yaml
source_name: tushare_like_offline
data_version: v0_3_drill
target_date: "2026-03-20"
output_root_dir: outputs/realdata
experiment_registry_dir: outputs/experiments
run_quality_report: true
run_leakage_audit: true
run_security_check: true
run_pipeline: true
build_frontend: true
build_dashboard: true
record_experiment: true
notes: "v0.3 real-data-offline drill using offline fixture"
```

## Commands

Run a drill:

```bash
python -m ashare_alpha run-realdata-offline-drill --spec configs/ashare_alpha/realdata/tushare_like_offline_drill.yaml
python -m ashare_alpha run-realdata-offline-drill --spec configs/ashare_alpha/realdata/akshare_like_offline_drill.yaml --format json
```

Show a saved result:

```bash
python -m ashare_alpha show-realdata-drill --path outputs/realdata/<drill_id>/drill_result.json
```

## Outputs

Each run creates `outputs/realdata/{drill_id}/` with:

- `drill_result.json`
- `drill_report.md`
- `step_summary.csv`
- `cache/`
- `materialized/`
- `validation/`
- optional `quality/`, `audit/`, `security/`, `pipeline/`, `frontend/`, and `dashboard/`

Imported data is written through the existing import layer under `data/imports/{source_name}/{data_version}/`.

## Status Rules

- Required step failure makes the drill `FAILED` and the CLI returns non-zero.
- Optional step failure makes the drill `PARTIAL` and the CLI returns zero.
- Skipped optional steps are recorded as `SKIPPED`.

## Safety Boundary

The drill is a rehearsal, not a data fetcher. It must remain offline and research-only:

- no external API calls
- no website scraping
- no vendor SDK imports
- no broker integration
- no automatic order placement
- no investment advice
- no guaranteed returns
