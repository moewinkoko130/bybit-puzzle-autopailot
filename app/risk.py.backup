from dataclasses import dataclass


@dataclass
class RiskSettings:
    risk_percent: float = 1.0
    stop_loss_percent: float = 1.0
    take_profit_percent: float = 2.0


def calculate_position_size(
    balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
) -> float:

    if balance <= 0:
        raise ValueError("Balance must be greater than zero.")

    if risk_percent <= 0:
        raise ValueError("Risk percent must be greater than zero.")

    if entry_price <= 0:
        raise ValueError("Entry price must be greater than zero.")

    risk_amount = balance * (risk_percent / 100)

    price_difference = abs(
        entry_price - stop_loss_price
    )

    if price_difference <= 0:
        raise ValueError(
            "Entry price and stop-loss price "
            "cannot be the same."
        )

    quantity = risk_amount / price_difference

    return quantity


def calculate_sl_tp(
    entry_price: float,
    signal: str,
    stop_loss_percent: float = 1.0,
    take_profit_percent: float = 2.0,
) -> dict:

    if entry_price <= 0:
        raise ValueError(
            "Entry price must be greater than zero."
        )

    if stop_loss_percent <= 0:
        raise ValueError(
            "Stop-loss percent must be greater than zero."
        )

    if take_profit_percent <= 0:
        raise ValueError(
            "Take-profit percent must be greater than zero."
        )

    signal = signal.upper()

    if signal == "BUY":

        stop_loss = entry_price * (
            1 - stop_loss_percent / 100
        )

        take_profit = entry_price * (
            1 + take_profit_percent / 100
        )

    elif signal == "SELL":

        stop_loss = entry_price * (
            1 + stop_loss_percent / 100
        )

        take_profit = entry_price * (
            1 - take_profit_percent / 100
        )

    else:

        return {
            "stop_loss": None,
            "take_profit": None,
        }

    return {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }


def risk_status() -> str:

    return (
        "Risk Management: "
        "Position Size + SL/TP - PAPER ONLY"
    )


if __name__ == "__main__":

    entry = 78000.0

    result = calculate_sl_tp(
        entry_price=entry,
        signal="BUY",
        stop_loss_percent=1.0,
        take_profit_percent=2.0,
    )

    print("Entry       :", entry)
    print(
        "Stop Loss   :",
        result["stop_loss"],
    )
    print(
        "Take Profit :",
        result["take_profit"],
    )
    print(
        "Status      :",
        risk_status(),
    )
