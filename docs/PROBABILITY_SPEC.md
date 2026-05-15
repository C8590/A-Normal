# PROBABILITY_SPEC

The baseline probability model estimates research-only win probability and expected return for future 5 / 10 / 20 trading-day horizons. It uses only local CSV data and existing `universe_daily`, `factor_daily`, `event_daily`, and `signal_daily` logic. It does not change BUY / WATCH / BLOCK generation, connect to brokers, submit orders, scrape websites, or call external APIs.

## train-probability-model

```bash
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20 --format json
python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20 --output-dir outputs/models/test_probability
```

The command validates local CSV data, builds a probability dataset, splits it by time into train/test samples, trains a pure Python score-bin calibrator, evaluates the test set, and writes:

- `probability_dataset.csv`
- `model.json`
- `metrics.json`
- `test_predictions.csv`
- `summary.md`

Default output directory:

```text
outputs/models/probability_START_END/
```

## predict-probabilities

```bash
python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20
python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20 --format json
```

The command loads `model.json`, builds same-day features using existing builders, and saves:

```text
outputs/probability/probability_daily_YYYY-MM-DD.csv
```

## Dataset Construction

For each trading date in the requested range, the dataset builder computes:

1. `universe_daily`
2. `factor_daily`
3. `event_daily`
4. `signal_daily`

Feature columns come only from records available on `trade_date` or earlier. Future prices are never used as features.

Rows may be filtered by configuration:

- `include_only_universe_allowed`
- `include_only_computable_factors`

## Labels

For each configured horizon `N`, the label builder finds the `N`th future trading bar for the same stock and computes:

```text
future_return_Nd = close(t + N trading days) / close(t) - 1
```

The win label is:

```text
y_win_Nd = 1 if future_return_Nd > win_return_threshold else 0
```

The comparison is strictly greater than the threshold. If the same-day trading bar is missing or there are not enough future trading bars, the future return and win label are `None`.

Future returns are training labels only. They are not prediction features.

## Time Split And Purge Gap

Records are sorted by unique `trade_date`.

```text
split_index = floor(unique_date_count * train_test_split_ratio)
```

Dates before `test_start_date` are train candidates; dates on or after `test_start_date` are test candidates. When `purge_gap=true`, the last `max(horizons)` training dates are removed before fitting. This prevents training labels near the boundary from using prices that fall inside the test period.

For dataset construction, local CSV may contain future prices after `end_date` so labels can be computed. Those future prices are labels only and are not used to build features.

## Score-Bin Calibration

The first model is `score_bin_calibrator`, a pure Python baseline:

1. Use `stock_score` as the score field.
2. Split training samples into up to `n_bins` score bins.
3. For each horizon and bin, count samples, wins, raw win rate, and mean future return.
4. Smooth win probability with the global train win rate:

```text
(win_count + prior_strength * global_win_rate) / (sample_count + prior_strength)
```

5. Smooth expected return with the global mean future return:

```text
(sum_future_return + prior_strength * global_mean_return) / (sample_count + prior_strength)
```

Prediction finds the score bin and outputs `p_win_Nd`, `expected_return_Nd`, bin index, bin sample count, and a confidence level.

## Metrics

Metrics are computed per horizon on the test set:

- `accuracy`: share of correct class predictions using `prediction_threshold`.
- `precision`: true positives divided by predicted positives; `None` if denominator is zero.
- `recall`: true positives divided by actual positives; `None` if denominator is zero.
- `AUC`: pure Python rank-based ROC AUC; `None` if only one class is present.
- `Brier score`: mean squared error between probability and binary label.
- `actual_win_rate`: positive labels divided by sample count.
- `average_future_return`: mean realized future return for valid labels.

## Risk Boundary

The model is for research and diagnostics only. It is not investment advice, does not promise future performance, and will not automatically place orders. A later version may replace this baseline with logistic regression or gradient boosting, but those models are not implemented in this task.
