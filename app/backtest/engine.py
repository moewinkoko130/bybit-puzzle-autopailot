from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.backtest.data import Candle
from app.strategy import ema_signal


@dataclass(frozen=True)
class BacktestConfig:
    """Execution and strategy parameters for a deterministic backtest."""

    initial_balance: float = 1000.0
    fast_period: int = 9
    slow_period: int = 21
    stop_loss_percent: float = 1.0
    reward_ratio: float = 2.0
    maker_fee: float = 0.0002
    taker_fee: float = 0.00055
    slippage: float = 0.0005
    fill_type: Literal["maker", "taker"] = "taker"
    risk_percent: float = 1.0

    def __post_init__(self) -> None:
        if self.initial_balance <= 0 or self.fast_period <= 0 or self.fast_period >= self.slow_period:
            raise ValueError("Invalid backtest balance or EMA periods.")
        if self.stop_loss_percent <= 0 or self.reward_ratio <= 0 or self.slippage < 0:
            raise ValueError("Invalid stop loss, reward ratio, or slippage.")
        if self.fill_type not in {"maker", "taker"} or not 0 < self.risk_percent <= 100:
            raise ValueError("Invalid fill type or risk percentage.")

    @property
    def fee_rate(self) -> float:
        return self.maker_fee if self.fill_type == "maker" else self.taker_fee


@dataclass(frozen=True)
class BacktestTrade:
    side: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    exit_reason: str

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.exit_time - self.entry_time).total_seconds())


@dataclass(frozen=True)
class BacktestResult:
    trades: list[BacktestTrade]
    equity_curve: list[float]
    initial_balance: float
    final_balance: float

    @property
    def total_pnl(self) -> float:
        return self.final_balance - self.initial_balance


class BacktestEngine:
    """Run a candle-by-candle EMA crossover simulation with realistic fills."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, candles: list[Candle]) -> BacktestResult:
        if not candles:
            return BacktestResult([], [self.config.initial_balance], self.config.initial_balance, self.config.initial_balance)
        closes: list[float] = []
        position: dict | None = None
        trades: list[BacktestTrade] = []
        equity = self.config.initial_balance
        curve = [equity]
        for candle in candles:
            closes.append(candle.close)
            if position is not None:
                exit_reason = self._exit_reason(position, candle)
                if exit_reason:
                    trade, equity = self._close(position, candle, exit_reason, equity)
                    trades.append(trade)
                    position = None
            if position is None and len(closes) >= self.config.slow_period + 1:
                signal = ema_signal(closes, self.config.fast_period, self.config.slow_period)
                if signal in {"BUY", "SELL"}:
                    entry = self._entry_price(candle.close, signal)
                    distance = entry * self.config.stop_loss_percent / 100
                    risk_amount = equity * self.config.risk_percent / 100
                    position = {
                        "side": signal,
                        "entry_time": candle.timestamp,
                        "entry_price": entry,
                        "quantity": risk_amount / distance,
                        "stop_loss": entry - distance if signal == "BUY" else entry + distance,
                        "take_profit": entry + distance * self.config.reward_ratio if signal == "BUY" else entry - distance * self.config.reward_ratio,
                    }
            curve.append(equity + (self._unrealized(position, candles[-1].close) if position else 0.0))
        if position is not None:
            trade, equity = self._close(position, candles[-1], "END_OF_DATA", equity)
            trades.append(trade)
            curve[-1] = equity
        return BacktestResult(trades, curve, self.config.initial_balance, equity)

    def _entry_price(self, close: float, side: str) -> float:
        return close * (1 + self.config.slippage if side == "BUY" else 1 - self.config.slippage)

    def _exit_price(self, position: dict, candle: Candle) -> float:
        if position["side"] == "BUY":
            return candle.low if candle.low <= position["stop_loss"] else candle.high if candle.high >= position["take_profit"] else candle.close
        return candle.high if candle.high >= position["stop_loss"] else candle.low if candle.low <= position["take_profit"] else candle.close

    def _exit_reason(self, position: dict, candle: Candle) -> str | None:
        if position["side"] == "BUY":
            if candle.low <= position["stop_loss"]:
                return "STOP_LOSS"
            if candle.high >= position["take_profit"]:
                return "TAKE_PROFIT"
        elif candle.high >= position["stop_loss"]:
            return "STOP_LOSS"
        elif candle.low <= position["take_profit"]:
            return "TAKE_PROFIT"
        return None

    def _close(self, position: dict, candle: Candle, reason: str, equity: float) -> tuple[BacktestTrade, float]:
        exit_price = self._exit_price(position, candle)
        if position["side"] == "BUY":
            filled_exit = exit_price * (1 - self.config.slippage)
            gross = (filled_exit - position["entry_price"]) * position["quantity"]
        else:
            filled_exit = exit_price * (1 + self.config.slippage)
            gross = (position["entry_price"] - filled_exit) * position["quantity"]
        fees = (position["entry_price"] * position["quantity"] + filled_exit * position["quantity"]) * self.config.fee_rate
        net = gross - fees
        trade = BacktestTrade(position["side"], position["entry_time"], candle.timestamp, position["entry_price"], filled_exit, position["quantity"], gross, fees, net, reason)
        return trade, equity + net

    @staticmethod
    def _unrealized(position: dict, price: float) -> float:
        if position["side"] == "BUY":
            return (price - position["entry_price"]) * position["quantity"]
        return (position["entry_price"] - price) * position["quantity"]
