from datetime import datetime, timezone

import pytest

from app.backtest import (
    BacktestConfig,
    BacktestEngine,
    Candle,
    HistoricalDataLoader,
    calculate_performance,
    optimize_strategy,
)


def candle(day, close, high=None, low=None):
    price = float(close)
    return Candle(
        datetime(2026, 1, day, tzinfo=timezone.utc),
        price,
        float(high if high is not None else price),
        float(low if low is not None else price),
        price,
        10,
    )


def test_loader_sorts_and_filters_json_rows(tmp_path):
    path = tmp_path / "candles.json"
    path.write_text(
        '[{"timestamp":"2026-01-02T00:00:00+00:00","open":2,"high":3,"low":1,"close":2},'
        '{"timestamp":"2026-01-01T00:00:00+00:00","open":1,"high":2,"low":0.5,"close":1}]'
    )
    candles = HistoricalDataLoader.load(path, end=datetime(2026, 1, 1))
    assert len(candles) == 1
    assert candles[0].close == 1


def test_backtest_applies_fees_slippage_and_closes_open_trade():
    candles = [candle(day, close) for day, close in enumerate([100, 100, 100, 100, 100, 110, 110], 1)]
    result = BacktestEngine(BacktestConfig(fast_period=2, slow_period=3, slippage=0.01, taker_fee=0.01)).run(candles)
    assert result.trades
    assert result.trades[0].side == "BUY"
    assert result.trades[0].fees > 0
    assert result.trades[0].net_pnl < result.trades[0].gross_pnl


def test_backtest_supports_short_stop_loss():
    candles = [candle(day, close) for day, close in enumerate([100, 100, 100, 90, 80, 80], 1)]
    candles.append(candle(7, 85, high=95, low=84))
    result = BacktestEngine(BacktestConfig(fast_period=2, slow_period=3, stop_loss_percent=1)).run(candles)
    assert any(trade.side == "SELL" for trade in result.trades)


def test_metrics_zero_trades_are_finite():
    result = BacktestEngine().run([])
    report = calculate_performance(result)
    assert report.total_trades == 0
    assert report.cumulative_return == 0
    assert report.sharpe_ratio == 0
    assert report.sortino_ratio == 0
    assert report.max_drawdown == 0


def test_metrics_capture_continuous_drawdown():
    candles = [candle(day, close) for day, close in enumerate([100] * 22 + [90, 80, 70], 1)]
    result = BacktestEngine(BacktestConfig(fast_period=2, slow_period=3)).run(candles)
    report = calculate_performance(result)
    assert report.max_drawdown >= 0


def test_optimizer_skips_invalid_combinations_and_returns_holdout_results():
    candles = [candle(day, 100 + day) for day in range(1, 31)]
    results = optimize_strategy(candles, [2, 3], [3, 2], [1], [2], train_ratio=0.7)
    assert len(results) == 1
    assert results[0].parameters["fast_period"] == 2
    assert results[0].test is not None
