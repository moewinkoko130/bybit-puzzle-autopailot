from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaperPosition:
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    opened_at: str = ""


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


def open_paper_position(
    signal: str,
    entry_price: float,
    quantity: float,
    stop_loss: float,
    take_profit: float,
) -> PaperPosition | None:

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
