from __future__ import annotations

from datetime import date

from a_normal.cli import main
from a_normal.factors import EventScoreResult, FactorDaily
from a_normal.signals import ScoringConfig, build_signals, load_scoring_config, save_signals_csv, save_signals_markdown
from a_normal.universe import UniverseDaily


def test_universe_rejection_must_block_signal():
    signals = build_signals(
        [UniverseDaily(ts_code="000001.SZ", is_allowed=False, exclude_reasons=("low_liquidity",), liquidity_score=0.1, risk_score=0.5)],
        [good_factor("000001.SZ")],
        [],
        market_regime="normal",
        as_of_date="2026-01-31",
        config=buy_config(),
    )

    assert signals[0].signal == "BLOCK"
    assert signals[0].target_weight == 0
    assert "股票池未通过" in signals[0].reason


def test_high_risk_must_block_signal():
    event = EventScoreResult(
        stock_code="000001.SZ",
        event_date="2026-01-31",
        event_type="investigation",
        event_score=-1,
        event_risk_score=0.95,
        event_block_buy=True,
        event_reason="立案调查",
    )

    signals = build_signals(
        [allowed_universe("000001.SZ")],
        [good_factor("000001.SZ")],
        [event],
        market_regime="normal",
        as_of_date="2026-01-31",
        config=buy_config(),
    )

    assert signals[0].risk_level == "high"
    assert signals[0].signal == "BLOCK"
    assert "高风险公告触发禁买" in signals[0].reason


def test_market_risk_regime_prohibits_buy_but_allows_watch():
    signals = build_signals(
        [allowed_universe("000001.SZ")],
        [good_factor("000001.SZ")],
        [],
        market_regime="risk",
        as_of_date="2026-01-31",
        config=buy_config(),
    )

    assert signals[0].stock_score >= 70
    assert signals[0].signal == "WATCH"
    assert signals[0].target_weight == 0
    assert "市场处于风险状态" in signals[0].reason


def test_target_weight_respects_capital_lot_size_and_single_name_cap():
    signals = build_signals(
        [allowed_universe("000001.SZ")],
        [good_factor("000001.SZ", close=10)],
        [],
        market_regime="normal",
        as_of_date="2026-01-31",
        config=buy_config(max_single_position_pct=0.5),
    )

    assert signals[0].signal == "BUY"
    assert signals[0].target_weight == 0.4
    assert "目标权重40.00%" in signals[0].reason


def test_low_score_generates_sell_signal_with_chinese_reason():
    signals = build_signals(
        [allowed_universe("000001.SZ")],
        [bad_factor("000001.SZ")],
        [],
        market_regime="normal",
        as_of_date="2026-01-31",
        config=buy_config(),
    )

    assert signals[0].signal == "SELL"
    assert "综合评分" in signals[0].reason
    assert "信号为SELL" in signals[0].reason


def test_signal_outputs_can_be_saved_as_csv_and_markdown(tmp_path):
    signals = build_signals(
        [allowed_universe("000001.SZ")],
        [good_factor("000001.SZ")],
        [],
        market_regime="normal",
        as_of_date="2026-01-31",
        config=buy_config(),
    )
    csv_path = tmp_path / "signals.csv"
    markdown_path = tmp_path / "signals.md"

    save_signals_csv(signals, csv_path)
    save_signals_markdown(signals, markdown_path)

    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "ts_code,trade_date,stock_score,risk_level,signal,target_weight,reason"
    assert "| 代码 | 信号 | 分数 | 风险 | 目标权重 | 原因 |" in markdown_path.read_text(encoding="utf-8")


def test_scoring_config_loads_from_yaml():
    config = load_scoring_config()

    assert config.capital == 10000
    assert config.lot_size == 100
    assert config.weights["momentum_20d"] > 0


def test_cli_generate_signals_writes_csv_and_markdown(tmp_path, capsys):
    exit_code = main(["generate-signals", "--date", "2026-03-26", "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "CSV:" in captured.out
    assert (tmp_path / "signals_2026-03-26.csv").exists()
    assert (tmp_path / "signals_2026-03-26.md").exists()


def allowed_universe(ts_code: str) -> UniverseDaily:
    return UniverseDaily(ts_code=ts_code, is_allowed=True, exclude_reasons=(), liquidity_score=1, risk_score=1)


def good_factor(ts_code: str, close: float = 10) -> FactorDaily:
    return FactorDaily(
        ts_code=ts_code,
        trade_date=date(2026, 1, 31),
        close=close,
        momentum_20d=0.2,
        close_above_ma20=True,
    )


def bad_factor(ts_code: str) -> FactorDaily:
    return FactorDaily(
        ts_code=ts_code,
        trade_date=date(2026, 1, 31),
        close=10,
        momentum_20d=-0.2,
        close_above_ma20=False,
    )


def buy_config(max_single_position_pct: float = 0.2) -> ScoringConfig:
    return ScoringConfig(
        capital=10000,
        lot_size=100,
        max_single_position_pct=max_single_position_pct,
        thresholds={
            "buy_score": 70,
            "watch_score": 55,
            "sell_score": 40,
            "high_risk_score": 0.7,
            "medium_risk_score": 0.4,
            "universe_high_risk_below": 0.3,
        },
        weights={
            "momentum_20d": 1.0,
            "close_above_ma20": 0.5,
            "universe_liquidity_score": 0.2,
            "universe_risk_score": 0.2,
            "event_risk_score": -0.5,
        },
        normalization={
            "momentum_abs_cap": 0.2,
            "volatility_cap": 0.08,
            "drawdown_cap": 0.2,
            "amount_mean_cap": 100000000,
            "turnover_mean_cap": 0.08,
            "limit_count_cap": 3,
        },
    )
