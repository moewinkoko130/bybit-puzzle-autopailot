from dataclasses import dataclass
from typing import Literal


Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class SignalEvent:
    action: Signal
    fast_ema: float | None
    slow_ema: float | None
    previous_fast_ema: float | None = None
    previous_slow_ema: float | None = None


def calculate_ema(
    prices: list[float],
    period: int,
) -> float | None:

    if period <= 0:
        raise ValueError(
            "EMA period must be greater than zero."
        )

    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(
        prices[:period]
    ) / period

    for price in prices[period:]:
        ema = (
            (price - ema)
            * multiplier
            + ema
        )

    return ema


def ema_signal(
    prices: list[float],
    fast_period: int = 9,
    slow_period: int = 21,
) -> Signal:

    if fast_period >= slow_period:
        raise ValueError(
            "Fast EMA period must be "
            "smaller than slow EMA period."
        )

    if len(prices) < slow_period + 1:
        return "HOLD"

    fast_ema = calculate_ema(
        prices,
        fast_period,
    )

    slow_ema = calculate_ema(
        prices,
        slow_period,
    )

    if fast_ema is None:
        return "HOLD"

    if slow_ema is None:
        return "HOLD"

    previous_fast_ema = calculate_ema(prices[:-1], fast_period)
    previous_slow_ema = calculate_ema(prices[:-1], slow_period)

    if previous_fast_ema is None or previous_slow_ema is None:
        return "HOLD"

    if previous_fast_ema <= previous_slow_ema and fast_ema > slow_ema:
        return "BUY"

    if previous_fast_ema >= previous_slow_ema and fast_ema < slow_ema:
        return "SELL"

    return "HOLD"


def strategy_status() -> str:
    return "EMA Crossover (9/21) - SIGNAL ONLY"


def analyze_prices(
    prices: list[float],
) -> dict:

    fast_ema = calculate_ema(
        prices,
        9,
    )

    slow_ema = calculate_ema(
        prices,
        21,
    )

    signal = ema_signal(
        prices,
        9,
        21,
    )

    return {
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "signal": signal,
        "event": SignalEvent(
            action=signal,
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            previous_fast_ema=calculate_ema(prices[:-1], 9),
            previous_slow_ema=calculate_ema(prices[:-1], 21),
        ),
    }


if __name__ == "__main__":

    sample_prices = [
        100,
        101,
        100.5,
        102,
        103,
        104,
        103.5,
        105,
        106,
        107,
        108,
        107.5,
        109,
        110,
        111,
        112,
        113,
        114,
        115,
        116,
        117,
    ]

    result = analyze_prices(
        sample_prices
    )

    print(
        "Strategy:",
        strategy_status(),
    )

    print(
        "Fast EMA:",
        result["fast_ema"],
    )

    print(
        "Slow EMA:",
        result["slow_ema"],
    )

    print(
        "Signal:",
        result["signal"],
    )
