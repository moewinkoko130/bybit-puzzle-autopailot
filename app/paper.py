import sqlite3
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4


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
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    reason: str
    opened_at: str
    closed_at: str
    trade_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    strategy: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0
    exit_reason: str = ""
    fees: float = 0.0
    slippage: float = 0.0
    gross_pnl: float | None = None
    net_pnl: float | None = None
    realized_pnl: float | None = None
    status: str = CLOSED

    def __post_init__(self):
        if not self.exit_reason:
            self.exit_reason = self.reason
        if self.gross_pnl is None:
            self.gross_pnl = self.pnl + self.fees
        if self.net_pnl is None:
            self.net_pnl = self.pnl
        if self.realized_pnl is None:
            self.realized_pnl = self.net_pnl


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaperExecutor:
    def __init__(
        self,
        database_path: str | Path = "logs/paper_positions.db",
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.database_path = str(database_path)
        self._clock = clock
        database = Path(database_path)
        if self.database_path != ":memory:":
            database.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._closed = False
        self._create_schema()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("PaperExecutor is closed.")

    def _create_schema(self) -> None:
        self._ensure_open()
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                trade_id TEXT PRIMARY KEY, symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL, strategy TEXT NOT NULL,
                side TEXT NOT NULL, entry_price REAL NOT NULL,
                quantity REAL NOT NULL, stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL, opened_at TEXT NOT NULL,
                closed_at TEXT, exit_price REAL, exit_reason TEXT,
                fees REAL NOT NULL DEFAULT 0, slippage REAL NOT NULL DEFAULT 0,
                gross_pnl REAL NOT NULL DEFAULT 0,
                net_pnl REAL NOT NULL DEFAULT 0,
                realized_pnl REAL NOT NULL DEFAULT 0, status TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in self._connection.execute(
                "PRAGMA table_info(paper_trades)"
            ).fetchall()
        }
        for column in ("gross_pnl", "net_pnl"):
            if column not in columns:
                self._connection.execute(
                    f"ALTER TABLE paper_trades ADD COLUMN {column} REAL NOT NULL DEFAULT 0"
                )
        self._connection.commit()

    @property
    def position(self) -> PaperPosition | None:
        self._ensure_open()
        row = self._connection.execute(
            "SELECT * FROM paper_trades WHERE status = ? LIMIT 1", (OPEN,)
        ).fetchone()
        if row is None:
            return None
        return self._position_from_row(row)

    def _position_from_row(self, row: sqlite3.Row) -> PaperPosition:
        return PaperPosition(
            side=row["side"], entry_price=row["entry_price"],
            quantity=row["quantity"], stop_loss=row["stop_loss"],
            take_profit=row["take_profit"], opened_at=row["opened_at"],
            trade_id=row["trade_id"], symbol=row["symbol"],
            timeframe=row["timeframe"], strategy=row["strategy"],
            status=row["status"],
        )

    def open_position(
        self,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        symbol: str = "",
        timeframe: str = "",
        strategy: str = "",
    ) -> PaperPosition:
        self._ensure_open()
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("Side must be BUY or SELL.")
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            raise ValueError("All prices must be greater than zero.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if self.position is not None:
            raise ValueError("A paper position already exists.")

        trade_id = uuid4().hex
        opened_at = self._clock().isoformat()
        self._connection.execute(
            """
            INSERT INTO paper_trades (
                trade_id, symbol, timeframe, strategy, side, entry_price,
                quantity, stop_loss, take_profit, opened_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trade_id, symbol, timeframe, strategy, side, entry_price,
             quantity, stop_loss, take_profit, opened_at, OPEN),
        )
        self._connection.commit()
        return self.position

    def check_exit(self, current_price: float) -> str:
        self._ensure_open()
        position = self.position
        if position is None:
            raise ValueError("No paper position is open.")
        return check_exit(position, current_price)

    def close_at_trigger(self, current_price: float) -> PaperTrade:
        reason = self.check_exit(current_price)
        if reason == OPEN:
            raise ValueError("Position has not reached an exit trigger.")
        return self.close_position(current_price, reason)

    def close_position(
        self,
        exit_price: float,
        exit_reason: str = MANUAL_CLOSE,
        fees: float = 0.0,
        slippage: float = 0.0,
    ) -> PaperTrade:
        self._ensure_open()
        position = self.position
        if position is None:
            raise ValueError("No paper position is open.")
        if exit_price <= 0:
            raise ValueError("Exit price must be greater than zero.")
        exit_reason = exit_reason.upper()
        if exit_reason not in EXIT_REASONS:
            raise ValueError("Invalid paper exit reason.")
        if fees < 0 or slippage < 0:
            raise ValueError("Fees and slippage cannot be negative.")
        gross_pnl = calculate_pnl(position, exit_price)
        net_pnl = gross_pnl - (slippage * position.quantity) - fees
        closed_at = self._clock().isoformat()
        self._connection.execute(
            """
            UPDATE paper_trades SET closed_at = ?, exit_price = ?,
                     exit_reason = ?, fees = ?, slippage = ?, gross_pnl = ?,
                     net_pnl = ?, realized_pnl = ?,
                status = ? WHERE trade_id = ? AND status = ?
            """,
            (closed_at, exit_price, exit_reason, fees, slippage,
                 gross_pnl, net_pnl, net_pnl, CLOSED, position.trade_id, OPEN),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM paper_trades WHERE trade_id = ?", (position.trade_id,)
        ).fetchone()
        return PaperTrade(
            side=row["side"], entry_price=row["entry_price"],
            exit_price=row["exit_price"], quantity=row["quantity"],
            pnl=row["net_pnl"], reason=row["exit_reason"],
            opened_at=row["opened_at"], closed_at=row["closed_at"],
            trade_id=row["trade_id"], symbol=row["symbol"],
            timeframe=row["timeframe"], strategy=row["strategy"],
            stop_loss=row["stop_loss"], take_profit=row["take_profit"],
            exit_reason=row["exit_reason"], fees=row["fees"],
            slippage=row["slippage"], realized_pnl=row["realized_pnl"],
            gross_pnl=row["gross_pnl"], net_pnl=row["net_pnl"],
            status=row["status"],
        )

    def closed_trades(self) -> list[PaperTrade]:
        self._ensure_open()
        rows = self._connection.execute(
            "SELECT * FROM paper_trades WHERE status = ? ORDER BY opened_at",
            (CLOSED,),
        ).fetchall()
        return [
            PaperTrade(
                side=row["side"], entry_price=row["entry_price"],
                exit_price=row["exit_price"], quantity=row["quantity"],
                pnl=row["net_pnl"], reason=row["exit_reason"],
                opened_at=row["opened_at"], closed_at=row["closed_at"],
                trade_id=row["trade_id"], symbol=row["symbol"],
                timeframe=row["timeframe"], strategy=row["strategy"],
                stop_loss=row["stop_loss"], take_profit=row["take_profit"],
                exit_reason=row["exit_reason"], fees=row["fees"],
                slippage=row["slippage"], realized_pnl=row["realized_pnl"],
                gross_pnl=row["gross_pnl"], net_pnl=row["net_pnl"],
                status=row["status"],
            )
            for row in rows
        ]

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> "PaperExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def open_paper_position(
    signal: str,
    entry_price: float,
    quantity: float,
    stop_loss: float,
    take_profit: float,
) -> PaperPosition | None:

    warnings.warn(
        "open_paper_position is deprecated; use PaperExecutor.open_position.",
        DeprecationWarning,
        stacklevel=2,
    )

    signal = signal.upper()

    if signal not in {"BUY", "SELL"}:
        return None

    if entry_price <= 0:
        return None

    if quantity <= 0:
        return None

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return PaperPosition(
        side=signal,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        opened_at=now,
    )


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

    warnings.warn(
        "close_paper_position is deprecated; use PaperExecutor.close_position.",
        DeprecationWarning,
        stacklevel=2,
    )

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
        side=position.side,
        entry_price=position.entry_price,
        exit_price=exit_price,
        quantity=position.quantity,
        pnl=pnl,
        reason=reason.upper(),
        opened_at=position.opened_at,
        closed_at=closed_at,
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
