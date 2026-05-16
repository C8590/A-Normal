from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.adjusted_research import summarize_backtest_comparison, summarize_factor_comparison


def test_factor_comparison_summary_from_csv(tmp_path: Path) -> None:
    path = tmp_path / "factor_price_source_compare.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "ts_code",
                "left_price_source",
                "right_price_source",
                "momentum_20d_diff",
                "momentum_60d_diff",
                "ma20_diff",
                "ma60_diff",
                "volatility_20d_diff",
                "close_above_ma20_changed",
                "close_above_ma60_changed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ts_code": "600000.SH",
                "left_price_source": "raw",
                "right_price_source": "qfq",
                "momentum_20d_diff": "0.02",
                "momentum_60d_diff": "-0.03",
                "ma20_diff": "1.5",
                "ma60_diff": "2.5",
                "volatility_20d_diff": "0.01",
                "close_above_ma20_changed": "True",
                "close_above_ma60_changed": "False",
            }
        )

    summary = summarize_factor_comparison(path)

    assert summary.left_price_source == "raw"
    assert summary.right_price_source == "qfq"
    assert summary.compared_count == 1
    assert summary.changed_ma20_count == 1
    assert summary.max_abs_momentum_60d_diff == 0.03


def test_backtest_comparison_summary_from_json(tmp_path: Path) -> None:
    path = tmp_path / "backtest_price_source_compare.json"
    path.write_text(
        json.dumps(
            {
                "left": "raw",
                "right": "hfq",
                "execution_price_source": "raw",
                "diff": {"total_return_diff": 0.1, "sharpe_diff": 0.2, "trade_count_diff": 3},
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_backtest_comparison(path)

    assert summary.right_price_source == "hfq"
    assert summary.total_return_diff == 0.1
    assert summary.trade_count_diff == 3
    assert summary.summary["execution_price_source"] == "raw"
