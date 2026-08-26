import os
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RiskResult:
    entry: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    risk_percent: float
    position_size: float


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str = ""


class RiskGatekeeper:
    def __init__(self, clock=datetime.now):
        self.clock = clock
        self.last_trade_at: datetime | None = None

    def validate(
        self,
        account_balance: float,
        daily_pnl: float = 0.0,
        consecutive_losses: int = 0,
        last_trade_at: datetime | None = None,
    ) -> RiskDecision:
        if account_balance <= 0:
            return RiskDecision(False, "Account balance must be greater than zero.")
        daily_limit = float(os.getenv("DAILY_LOSS_LIMIT", "5.0"))
        max_losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
        cooldown = int(os.getenv("POST_TRADE_COOLDOWN_SECONDS", "0"))
        if daily_pnl <= -(account_balance * daily_limit / 100):
            return RiskDecision(False, "Daily loss limit reached.")
        if consecutive_losses >= max_losses:
            return RiskDecision(False, "Maximum consecutive losses reached.")
        trade_time = last_trade_at or self.last_trade_at
        if trade_time is not None:
            if self.clock() - trade_time < timedelta(seconds=cooldown):
                return RiskDecision(False, "Post-trade cooldown is active.")
        return RiskDecision(True)


def get_risk_percent() -> float:
    value = os.getenv(
        "MAX_RISK_PERCENT",
        "1.0",
    ).strip()

    try:
        risk = float(value)
    except ValueError:
        risk = 1.0

    if risk <= 0:
        risk = 1.0

    if risk > 100:
        risk = 100.0

    return risk


def calculate_risk(
    entry: float,
    account_balance: float,
    stop_loss_percent: float = 1.0,
    reward_ratio: float = 2.0,
    side: str = "BUY",
) -> RiskResult:

    if entry <= 0:
        raise ValueError("Entry price must be greater than zero.")

    if account_balance <= 0:
        raise ValueError(
            "Account balance must be greater than zero."
        )

    if stop_loss_percent <= 0:
        raise ValueError(
            "Stop-loss percentage must be greater than zero."
        )

    if reward_ratio <= 0:
        raise ValueError(
            "Reward ratio must be greater than zero."
        )

    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("Side must be BUY or SELL.")

    risk_percent = get_risk_percent()

    risk_amount = (
        account_balance
        * risk_percent
        / 100
    )

    risk_distance = entry * stop_loss_percent / 100
    if side == "BUY":
        stop_loss = entry - risk_distance
        take_profit = entry + risk_distance * reward_ratio
    else:
        stop_loss = entry + risk_distance
        take_profit = entry - risk_distance * reward_ratio

    price_risk = abs(entry - stop_loss)

    position_size = (
        risk_amount / price_risk
        if price_risk > 0
        else 0.0
    )

    return RiskResult(
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_amount=risk_amount,
        risk_percent=risk_percent,
        position_size=position_size,
    )


def risk_status() -> str:
    return (
        "Risk Management: "
        "Position Size + SL/TP - PAPER ONLY"
    )


if __name__ == "__main__":

    entry = 78000.0
    balance = 1000.0

    result = calculate_risk(
        entry=entry,
        account_balance=balance,
        stop_loss_percent=1.0,
        reward_ratio=2.0,
    )

    print("=== RISK TEST ===")
    print()
    print(f"Account Balance : {balance:.2f}")
    print(f"Risk Percent    : {result.risk_percent:.2f}%")
    print(f"Risk Amount     : {result.risk_amount:.2f}")
    print(f"Entry           : {result.entry:.2f}")
    print(f"Stop Loss       : {result.stop_loss:.2f}")
    print(f"Take Profit     : {result.take_profit:.2f}")
    print(f"Position Size   : {result.position_size:.6f}")
    print()
    print(f"Status          : {risk_status()}")
    print()
    print("✓ PAPER ONLY")
    print("✓ No real order was placed.")
