import math
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


OPEN = "OPEN"
CLOSED = "CLOSED"
STOP_LOSS = "STOP_LOSS"
TAKE_PROFIT = "TAKE_PROFIT"
MANUAL_CLOSE = "MANUAL_CLOSE"
EXIT_REASONS = {STOP_LOSS, TAKE_PROFIT, MANUAL_CLOSE}


@dataclass
class PaperPosition:
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    opened_at: str = ""
    trade_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    strategy: str = ""
    status: str = OPEN


@dataclass
class PaperTrade:
    trade_id: str
    symbol: str
    timeframe: str
    strategy: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    exit_reason: str
    opened_at: str
    closed_at: str
    status: str = CLOSED
    fees: float = 0.0
    slippage: float = 0.0

    @property
    def reason(self) -> str:
        return self.exit_reason


class PaperExecutor:
    """Deterministic, paper-only execution boundary backed by SQLite."""

    def __init__(self, db_path: str = ":memory:", clock: Callable[[], datetime] | None = None,
                 fee_rate: float = 0.0, slippage: float = 0.0) -> None:
        if fee_rate < 0 or slippage < 0:
            raise ValueError("Fee rate and slippage cannot be negative.")
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
            strategy TEXT NOT NULL, side TEXT NOT NULL, entry_price REAL NOT NULL,
            quantity REAL NOT NULL, stop_loss REAL NOT NULL, take_profit REAL NOT NULL,
            opened_at TEXT NOT NULL, closed_at TEXT, exit_price REAL, exit_reason TEXT,
            fees REAL NOT NULL DEFAULT 0, slippage REAL NOT NULL DEFAULT 0,
            realized_pnl REAL, status TEXT NOT NULL)"""
        )
        self.connection.commit()

    @staticmethod
    def _validate_price(value: float, label: str) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{label} must be greater than zero.")

    @staticmethod
    def _validate_position(side: str, entry: float, stop_loss: float, take_profit: float) -> None:
        if side == "BUY" and not stop_loss < entry < take_profit:
            raise ValueError("BUY stop loss must be below entry and take profit above entry.")
        if side == "SELL" and not take_profit < entry < stop_loss:
            raise ValueError("SELL stop loss must be above entry and take profit below entry.")

    @property
    def position(self) -> PaperPosition | None:
        row = self.connection.execute(
            "SELECT * FROM paper_trades WHERE status = ? ORDER BY opened_at LIMIT 1", (OPEN,)
        ).fetchone()
        if row is None:
            return None
        return PaperPosition(
            trade_id=row["trade_id"], symbol=row["symbol"], timeframe=row["timeframe"],
            strategy=row["strategy"], side=row["side"], entry_price=row["entry_price"],
            quantity=row["quantity"], stop_loss=row["stop_loss"], take_profit=row["take_profit"],
            opened_at=row["opened_at"], status=row["status"],
        )

    def open_position(self, signal: str, entry_price: float, quantity: float, stop_loss: float,
                      take_profit: float, symbol: str = "", timeframe: str = "", strategy: str = "",
                      trade_id: str | None = None, opened_at: str | None = None) -> PaperPosition:
        side = signal.upper().strip()
        if side not in {"BUY", "SELL"}:
            raise ValueError("Signal must be BUY or SELL.")
        if not math.isfinite(quantity) or quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        self._validate_price(entry_price, "Entry price")
        self._validate_price(stop_loss, "Stop loss")
        self._validate_price(take_profit, "Take profit")
        self._validate_position(side, entry_price, stop_loss, take_profit)
        if self.position is not None:
            raise ValueError("An open paper position already exists.")
        position = PaperPosition(
            trade_id=trade_id or str(uuid.uuid4()), symbol=symbol, timeframe=timeframe,
            strategy=strategy, side=side, entry_price=entry_price, quantity=quantity,
            stop_loss=stop_loss, take_profit=take_profit,
            opened_at=opened_at or self.clock().isoformat(),
        )
        self.connection.execute(
            """INSERT INTO paper_trades
            (trade_id, symbol, timeframe, strategy, side, entry_price, quantity,
             stop_loss, take_profit, opened_at, fees, slippage, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (position.trade_id, position.symbol, position.timeframe, position.strategy,
             position.side, position.entry_price, position.quantity, position.stop_loss,
             position.take_profit, position.opened_at, self.slippage, OPEN),
        )
        self.connection.commit()
        return position

    def close_position(self, exit_price: float, reason: str = MANUAL_CLOSE) -> PaperTrade:
        position = self.position
        if position is None:
            raise ValueError("There is no open paper position.")
        reason = reason.upper().strip()
        if reason not in EXIT_REASONS:
            raise ValueError(f"Invalid exit reason: {reason}.")
        self._validate_price(exit_price, "Exit price")
        effective_exit = exit_price * (1 - self.slippage if position.side == "BUY" else 1 + self.slippage)
        gross_pnl = calculate_pnl(position, effective_exit)
        fees = (position.entry_price * position.quantity + effective_exit * position.quantity) * self.fee_rate
        trade = PaperTrade(
            trade_id=position.trade_id, symbol=position.symbol, timeframe=position.timeframe,
            strategy=position.strategy, side=position.side, entry_price=position.entry_price,
            exit_price=effective_exit, quantity=position.quantity, pnl=gross_pnl - fees,
            exit_reason=reason, opened_at=position.opened_at, closed_at=self.clock().isoformat(),
            fees=fees, slippage=self.slippage,
        )
        self.connection.execute(
            """UPDATE paper_trades SET closed_at = ?, exit_price = ?, exit_reason = ?,
            fees = ?, realized_pnl = ?, status = ? WHERE trade_id = ?""",
            (trade.closed_at, trade.exit_price, trade.exit_reason, trade.fees,
             trade.pnl, CLOSED, trade.trade_id),
        )
        self.connection.commit()
        return trade

    def check_exit(self, current_price: float) -> str:
        position = self.position
        if position is None:
            return CLOSED
        self._validate_price(current_price, "Current price")
        return check_exit(position, current_price)

    def close_at_trigger(self, current_price: float) -> PaperTrade | None:
        reason = self.check_exit(current_price)
        return None if reason == OPEN else self.close_position(current_price, reason)

    def closed_trades(self) -> list[PaperTrade]:
        rows = self.connection.execute(
            "SELECT * FROM paper_trades WHERE status = ? ORDER BY closed_at", (CLOSED,)
        ).fetchall()
        return [PaperTrade(
            trade_id=row["trade_id"], symbol=row["symbol"], timeframe=row["timeframe"],
            strategy=row["strategy"], side=row["side"], entry_price=row["entry_price"],
            exit_price=row["exit_price"], quantity=row["quantity"], pnl=row["realized_pnl"],
            exit_reason=row["exit_reason"], opened_at=row["opened_at"], closed_at=row["closed_at"],
            fees=row["fees"], slippage=row["slippage"],
        ) for row in rows]

    def close(self) -> None:
        self.connection.close()


def open_paper_position(
    signal: str,
    entry_price: float,
    quantity: float,
    stop_loss: float,
    take_profit: float,
) -> PaperPosition | None:

    try:
        return PaperExecutor().open_position(signal, entry_price, quantity, stop_loss, take_profit)
    except ValueError:
        return None


def calculate_pnl(
    position: PaperPosition,
    current_price: float,
) -> float:

    if position.side == "BUY":
        return (
            current_price - position.entry_price
        ) * position.quantity

    if position.side == "SELL":
        return (
            position.entry_price - current_price
        ) * position.quantity

    return 0.0


def check_exit(
    position: PaperPosition,
    current_price: float,
) -> str:

    if position.side == "BUY":

        if current_price <= position.stop_loss:
            return "STOP_LOSS"

        if current_price >= position.take_profit:
            return "TAKE_PROFIT"

    elif position.side == "SELL":

        if current_price >= position.stop_loss:
            return "STOP_LOSS"

        if current_price <= position.take_profit:
            return "TAKE_PROFIT"

    return "OPEN"


def close_paper_position(
    position: PaperPosition,
    exit_price: float,
    reason: str,
) -> PaperTrade:

    if exit_price <= 0:
        raise ValueError(
            "Exit price must be greater than zero."
        )

    pnl = calculate_pnl(
        position,
        exit_price,
    )

    closed_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return PaperTrade(
        trade_id=position.trade_id, symbol=position.symbol, timeframe=position.timeframe,
        strategy=position.strategy, side=position.side, entry_price=position.entry_price,
        exit_price=exit_price, quantity=position.quantity, pnl=pnl,
        exit_reason=reason.upper(), opened_at=position.opened_at, closed_at=closed_at,
    )


def calculate_statistics(
    trades: list[PaperTrade],
) -> dict:

    total_trades = len(trades)

    if total_trades == 0:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "average_pnl": 0.0,
        }

    wins = sum(
        1
        for trade in trades
        if trade.pnl > 0
    )

    losses = sum(
        1
        for trade in trades
        if trade.pnl < 0
    )

    breakeven = sum(
        1
        for trade in trades
        if trade.pnl == 0
    )

    total_pnl = sum(
        trade.pnl
        for trade in trades
    )

    average_pnl = (
        total_pnl / total_trades
    )

    win_rate = (
        wins / total_trades * 100
    )

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "average_pnl": average_pnl,
    }


def format_paper_trade(
    trade: PaperTrade,
) -> str:

    return (
        f"{trade.closed_at} | "
        f"{trade.side} | "
        f"Entry={trade.entry_price:.2f} | "
        f"Exit={trade.exit_price:.2f} | "
        f"Qty={trade.quantity:.6f} | "
        f"PnL={trade.pnl:+.4f} | "
        f"Reason={trade.reason}"
    )


def print_statistics(
    trades: list[PaperTrade],
) -> None:

    stats = calculate_statistics(
        trades
    )

    print()
    print("=== PAPER PERFORMANCE ===")
    print()
    print(
        f"Total Trades : "
        f"{stats['total_trades']}"
    )
    print(
        f"Wins         : "
        f"{stats['wins']}"
    )
    print(
        f"Losses       : "
        f"{stats['losses']}"
    )
    print(
        f"Breakeven    : "
        f"{stats['breakeven']}"
    )
    print(
        f"Win Rate     : "
        f"{stats['win_rate']:.2f}%"
    )
    print(
        f"Total PnL    : "
        f"{stats['total_pnl']:+.4f}"
    )
    print(
        f"Average PnL  : "
        f"{stats['average_pnl']:+.4f}"
    )


if __name__ == "__main__":

    trades = []

    # -----------------------------
    # Test BUY trade
    # -----------------------------

    buy_position = open_paper_position(
        signal="BUY",
        entry_price=78000.0,
        quantity=0.01,
        stop_loss=77220.0,
        take_profit=79560.0,
    )

    if buy_position:

        buy_trade = close_paper_position(
            buy_position,
            exit_price=79560.0,
            reason="TAKE_PROFIT",
        )

        trades.append(buy_trade)

    # -----------------------------
    # Test SELL trade
    # -----------------------------

    sell_position = open_paper_position(
        signal="SELL",
        entry_price=78000.0,
        quantity=0.01,
        stop_loss=78780.0,
        take_profit=76440.0,
    )

    if sell_position:

        sell_trade = close_paper_position(
            sell_position,
            exit_price=78780.0,
            reason="STOP_LOSS",
        )

        trades.append(sell_trade)

    print("=== PAPER TRADE HISTORY ===")
    print()

    for index, trade in enumerate(
        trades,
        start=1,
    ):

        print(
            f"{index}. "
            f"{format_paper_trade(trade)}"
        )

    print_statistics(
        trades
    )

    print()
    print("✓ PAPER ONLY")
    print("✓ No real order was placed.")
