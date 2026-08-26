from dataclasses import dataclass


@dataclass
class PaperPosition:
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float


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

    return PaperPosition(
        side=signal,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
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
        print("Side        :", position.side)
        print("Entry Price :", position.entry_price)
        print("Quantity    :", position.quantity)
        print("Stop Loss   :", position.stop_loss)
        print("Take Profit :", position.take_profit)

        current_price = 78500.0

        print()
        print("Current     :", current_price)
        print(
            "PnL         :",
            calculate_pnl(
                position,
                current_price,
            ),
        )
        print(
            "Status      :",
            check_exit(
                position,
                current_price,
            ),
        )

        print()
        print("✓ PAPER ONLY")
        print("✓ No real order was placed.")
