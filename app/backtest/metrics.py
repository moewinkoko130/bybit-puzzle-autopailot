from dataclasses import dataclass
from math import inf, sqrt
from statistics import mean, pstdev

from app.backtest.engine import BacktestResult


@dataclass(frozen=True)
class PerformanceReport:
    """Risk and return statistics for a backtest result."""

    cumulative_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    duration_distribution: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def calculate_performance(result: BacktestResult, periods_per_year: int = 252) -> PerformanceReport:
    """Calculate returns, risk-adjusted ratios, drawdown, and duration statistics."""
    trades = result.trades
    returns = [trade.net_pnl / result.initial_balance for trade in trades]
    average = mean(returns) if returns else 0.0
    deviation = pstdev(returns) if len(returns) > 1 else 0.0
    downside = [value for value in returns if value < 0]
    downside_deviation = sqrt(sum(value * value for value in downside) / len(downside)) if downside else 0.0
    sharpe = (average / deviation * sqrt(periods_per_year)) if deviation else 0.0
    sortino = (average / downside_deviation * sqrt(periods_per_year)) if downside_deviation else 0.0
    wins = [value for value in returns if value > 0]
    losses = [-value for value in returns if value < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    equity = result.initial_balance
    peak = equity
    drawdown = 0.0
    for trade in trades:
        equity += trade.net_pnl
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    durations = [trade.duration_seconds for trade in trades]
    distribution = {
        "min_seconds": min(durations) if durations else 0.0,
        "average_seconds": mean(durations) if durations else 0.0,
        "max_seconds": max(durations) if durations else 0.0,
    }
    return PerformanceReport(
        cumulative_return=(result.final_balance / result.initial_balance - 1) if result.initial_balance else 0.0,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=drawdown,
        win_rate=(len(wins) / len(trades) if trades else 0.0),
        profit_factor=(gross_profit / gross_loss if gross_loss else (inf if gross_profit else 0.0)),
        total_trades=len(trades),
        duration_distribution=distribution,
    )


def format_report(report: PerformanceReport) -> str:
    """Render a concise text report for CLI and logs."""
    return "\n".join([
        f"Cumulative Return: {report.cumulative_return:.2%}",
        f"Sharpe Ratio: {report.sharpe_ratio:.3f}",
        f"Sortino Ratio: {report.sortino_ratio:.3f}",
        f"Max Drawdown: {report.max_drawdown:.4f}",
        f"Win Rate: {report.win_rate:.2%}",
        f"Profit Factor: {report.profit_factor:.3f}",
        f"Total Trades: {report.total_trades}",
        f"Trade Duration (seconds): {report.duration_distribution}",
    ])
