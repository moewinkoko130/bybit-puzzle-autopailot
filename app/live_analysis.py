import os

from app.market import get_candles
from app.strategy import analyze_prices


def live_strategy_analysis() -> None:
    symbol = os.getenv(
        "BYBIT_SYMBOL",
        "BTCUSDT",
    ).strip().upper()

    timeframe = os.getenv(
        "BYBIT_TIMEFRAME",
        "5",
    ).strip()

    testnet = (
        os.getenv(
            "BYBIT_TESTNET",
            "true",
        ).lower()
        == "true"
    )

    print()
    print("=" * 45)
    print("          LIVE MARKET ANALYSIS")
    print("=" * 45)

    print(f"Environment : {'TESTNET' if testnet else 'MAINNET'}")
    print(f"Symbol      : {symbol}")
    print(f"Timeframe   : {timeframe} minutes")
    print()
    print("Fetching candle data from Bybit...")

    try:
        prices = get_candles(
            symbol=symbol,
            interval=timeframe,
            limit=100,
            testnet=testnet,
        )

        if len(prices) < 21:
            print()
            print("✗ Not enough candle data.")
            print(
                f"Received: {len(prices)} candles"
            )
            print("Required: 21 candles minimum")
            return

        result = analyze_prices(prices)

        fast_ema = result["fast_ema"]
        slow_ema = result["slow_ema"]
        signal = result["signal"]

        print()
        print("=============================================")
        print("             STRATEGY ANALYSIS")
        print("=============================================")

        print(f"Symbol       : {symbol}")
        print(f"Last Price   : {prices[-1]:.2f}")
        print(f"EMA 9        : {fast_ema:.2f}")
        print(f"EMA 21       : {slow_ema:.2f}")
        print(f"Signal       : {signal}")

        print()
        print("Strategy     : EMA Crossover")
        print("Fast EMA     : 9")
        print("Slow EMA     : 21")
        print("Mode         : SAFE / SIGNAL ONLY")

        print()
        print("✓ Live market data retrieved.")
        print("✓ Strategy calculation completed.")
        print("✓ No trading order was placed.")

        print("=============================================")

    except Exception as exc:
        print()
        print("✗ Live analysis failed.")
        print(f"Error: {exc}")

    print()
