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
            current_price
            - position.entry_price
        ) * position.quantity

    if position.side == "SELL":

        return (
            position.entry_price
            - current_price
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

    reason = reason.upper()

    if reason not in {
        "STOP_LOSS",
        "TAKE_PROFIT",
        "MANUAL",
        "SIGNAL_CHANGE",
    }:
        reason = "MANUAL"

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
        reason=reason,
        opened_at=position.opened_at,
        closed_at=closed_at,
    )


def format_paper_trade(
    trade: PaperTrade,
) -> str:

    return (
        f"{trade.closed_at} | "
        f"{trade.side} | "
        f"Entry={trade.entry_price:.2f} | "
        f"Exit={trade.exit_price:.2f} | "
        f"Qty={trade.quantity:.6f} | "
        f"PnL={trade.pnl:.4f} | "
        f"Reason={trade.reason}"
    )


if __name__ == "__main__":

    position = open_paper_position(
        signal="BUY",
        entry_price=78000.0,
        quantity=0.01,
        stop_loss=77220.0,
        take_profit=79560.0,
    )

    if position:

        print("=== PAPER POSITION ===")
        print(
            "Side        :",
            position.side,
        )
        print(
            "Entry Price :",
            position.entry_price,
        )
        print(
            "Quantity    :",
            position.quantity,
        )
        print(
            "Stop Loss   :",
            position.stop_loss,
        )
        print(
            "Take Profit :",
            position.take_profit,
        )
        print(
            "Opened At   :",
            position.opened_at,
        )

        current_price = 78500.0

        print()
        print(
            "Current     :",
            current_price,
        )

        pnl = calculate_pnl(
            position,
            current_price,
        )

        status = check_exit(
            position,
            current_price,
        )

        print(
            "PnL         :",
            pnl,
        )

        print(
            "Status      :",
            status,
        )

        if status != "OPEN":

            trade = close_paper_position(
                position,
                current_price,
                status,
            )

            print()
            print("=== PAPER TRADE CLOSED ===")
            print(
                format_paper_trade(
                    trade
                )
            )

        print()
        print("✓ PAPER ONLY")
        print("✓ No real order was placed.")
