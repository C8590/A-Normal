# Research Frontend Spec

## Scope

`build-frontend` creates a local read-only static HTML frontend from existing `outputs/` research artifacts. It is for inspection and reporting only.

It does not call external APIs, use a CDN, run npm, connect to brokers, submit orders, modify configs, or change research logic.

## Commands

```bash
python -m ashare_alpha build-frontend
python -m ashare_alpha build-frontend --format json
python -m ashare_alpha build-frontend --update-latest
python -m ashare_alpha serve-frontend --dir outputs/frontend/latest
```

`build-frontend` options:

- `--outputs-root PATH`: research outputs root. Default: `outputs`.
- `--output-dir PATH`: generated site directory. Default: `outputs/frontend/frontend_YYYYMMDD_HHMMSS`.
- `--update-latest`: also sync the generated site to `outputs/frontend/latest`.
- `--format text/json`: command output format. Default: `text`.

`serve-frontend` options:

- `--dir PATH`: generated frontend directory. Required.
- `--host TEXT`: bind host. Default: `127.0.0.1`.
- `--port INT`: bind port. Default: `8765`.

The server uses Python standard library `http.server`, serves static files only, and exposes no API. Non-localhost hosts print a warning.

## Output Layout

```text
outputs/frontend/frontend_YYYYMMDD_HHMMSS/
  index.html
  assets/
    app.js
    style.css
  frontend_data.json
```

`assets/app.js` embeds the same frontend data written to `frontend_data.json`, so `index.html` can be opened directly with `file://`.

## Data Collection

The collector reuses `DashboardScanner` and `build_dashboard_summary` to scan existing research outputs. Failed reads are represented as warning items instead of failing the full frontend build. Empty outputs still generate an empty dashboard page.

Displayed sections:

- Overview cards
- Latest Pipeline
- Latest Backtest
- Sweep
- Walk-forward
- Candidate table
- Recent Experiments
- Warning list
- Artifact Explorer with search, type filter, summary expansion, and sorting by `created_at`, `artifact_type`, and `status`

## Safety Boundary

The frontend is read-only. It does not execute research commands, modify files, edit configs, connect to broker APIs, place live orders, or claim guaranteed returns.

Page footer:

> 研究用途，不构成投资建议，不保证收益，不自动下单，未接券商接口。
