from dataclasses import dataclass
from itertools import product
from typing import Iterable

from app.backtest.data import Candle
from app.backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from app.backtest.metrics import PerformanceReport, calculate_performance


@dataclass(frozen=True)
class OptimizationResult:
    """One parameter combination evaluated on train and holdout data."""

    parameters: dict[str, float | int]
    train: PerformanceReport
    test: PerformanceReport


def optimize_strategy(
    candles: list[Candle],
    fast_periods: Iterable[int],
    slow_periods: Iterable[int],
    stop_loss_percents: Iterable[float],
    reward_ratios: Iterable[float],
    base_config: BacktestConfig | None = None,
    train_ratio: float = 0.7,
) -> list[OptimizationResult]:
    """Grid-search parameters and rank results by out-of-sample return."""
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between zero and one.")
    split = max(1, min(len(candles) - 1, int(len(candles) * train_ratio)))
    train_candles, test_candles = candles[:split], candles[split:]
    base = base_config or BacktestConfig()
    results: list[OptimizationResult] = []
    for fast, slow, stop_loss, reward in product(fast_periods, slow_periods, stop_loss_percents, reward_ratios):
        if fast >= slow:
            continue
        config = BacktestConfig(
            initial_balance=base.initial_balance,
            fast_period=int(fast), slow_period=int(slow),
            stop_loss_percent=float(stop_loss), reward_ratio=float(reward),
            maker_fee=base.maker_fee, taker_fee=base.taker_fee,
            slippage=base.slippage, fill_type=base.fill_type,
            risk_percent=base.risk_percent,
        )
        train_result = BacktestEngine(config).run(train_candles)
        test_result = BacktestEngine(config).run(test_candles)
        results.append(OptimizationResult(
            {"fast_period": int(fast), "slow_period": int(slow), "stop_loss_percent": float(stop_loss), "reward_ratio": float(reward)},
            calculate_performance(train_result), calculate_performance(test_result),
        ))
    return sorted(results, key=lambda item: item.test.cumulative_return, reverse=True)
