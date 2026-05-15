# Announcement Event Spec

`event_daily` is the daily announcement event factor table. It summarizes local `announcement_event.csv` rows into stock-level event signals for one `trade_date`.

The event engine is research-only. It is a transparent rule model and is not investment advice, a return guarantee, a trading signal, or an order-routing system.

## CLI

```bash
python -m ashare_alpha compute-events --date 2026-03-20
python -m ashare_alpha compute-events --date 2026-03-20 --format json
python -m ashare_alpha compute-events --date 2026-03-20 --output outputs/events/test.csv
```

Defaults:

- data directory: `data/sample/ashare_alpha`
- config directory: `configs/ashare_alpha`
- output: `outputs/events/event_daily_YYYY-MM-DD.csv`

The command validates local CSV data before building features. A validation failure returns a non-zero exit code.

## Event Classification

Known `event_type` values are used directly. Empty or `unknown` values are classified from title keywords such as 回购, 增持, 减持, 行政处罚, 立案调查, 诉讼, 仲裁, 合同, 中标, 业绩预增, 业绩预亏, 质押, and 解禁. Unmatched events remain `unknown`.

## Single Event Scoring

Only events with `event_time.date() <= trade_date` can be used. Future announcements are ignored. Events older than `event_scoring.event_window_days` are ignored.

Age:

```text
event_age_days = trade_date - event_time.date()
```

Decay:

```text
decay_weight = 0.5 ** (event_age_days / decay_half_life_days)
```

Event score:

```text
signed_event_score =
    base_score
    * event_strength
    * decay_weight
    * source_weight
```

Neutral events use a smaller score multiplier. Base scores, source weights, window length, and half-life all come from `configs/ashare_alpha/factors.yaml`.

Risk score:

```text
risk_score =
    risk_base
    * event_strength
    * decay_weight
    * risk_level_weight
```

The final risk score is clamped to `[0, 100]`.

## Block-Buy Rule

An individual event triggers `event_block_buy` when any condition is true:

- normalized event type is in `block_buy_event_types`
- event risk level is `high` and the type is in `high_risk_event_types`
- computed risk score is at least `80`

This is a research risk flag only. It is not an order instruction.

## Stock-Level Aggregation

For each stock and `trade_date`, `EventFeatureBuilder` uses only valid events on or before `trade_date` within the configured event window.

If `stock_master` is provided, every stock receives an `EventDailyRecord`. Stocks without valid events receive:

```text
event_score = 0
event_risk_score = 0
event_count = 0
event_block_buy = false
event_reason = 近窗口内无有效公告事件
```

Aggregation rules:

- `event_score`: sum of valid event scores, clamped to `[-100, 100]`
- `event_risk_score`: maximum valid event risk score
- `event_count`: number of valid events
- `positive_event_count`: valid events with positive signed score
- `negative_event_count`: valid events with negative signed score
- `high_risk_event_count`: valid events with risk score at least `60` or risk level `high`
- `event_block_buy`: true if any valid event triggers block-buy
- `latest_event_title`: most recent valid event title
- `latest_negative_event_title`: most recent valid negative event title
- `event_reason`: Chinese readable summary

The output is sorted by `ts_code`.
