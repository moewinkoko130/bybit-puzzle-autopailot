import os
import time
from datetime import datetime

from app.market import get_candles
from app.strategy import analyze_prices
from app.risk import calculate_risk
from app.paper import (
    PaperPosition,
    PaperTrade,
    calculate_pnl,
    check_exit,
    format_paper_trade,
    PaperExecutor,
)


def get_settings():
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

    return symbol, timeframe, testnet


def get_paper_balance() -> float:
    value = os.getenv(
        "PAPER_ACCOUNT_BALANCE",
        "1000.0",
    ).strip()

    try:
        balance = float(value)
    except ValueError:
        balance = 1000.0

    if balance <= 0:
        balance = 1000.0

    return balance


def get_stop_loss_percent() -> float:
    value = os.getenv(
        "PAPER_STOP_LOSS_PERCENT",
        "1.0",
    ).strip()

    try:
        percent = float(value)
    except ValueError:
        percent = 1.0

    if percent <= 0:
        percent = 1.0

    return percent


def get_reward_ratio() -> float:
    value = os.getenv(
        "PAPER_REWARD_RATIO",
        "2.0",
    ).strip()

    try:
        ratio = float(value)
    except ValueError:
        ratio = 2.0

    if ratio <= 0:
        ratio = 2.0

    return ratio


def print_position(
    position: PaperPosition,
    current_price: float,
) -> None:

    pnl = calculate_pnl(
        position,
        current_price,
    )

    status = check_exit(
        position,
        current_price,
    )

    print()
    print("=== PAPER POSITION ===")
    print(
        f"Side        : {position.side}"
    )
    print(
        f"Entry Price : {position.entry_price:.2f}"
    )
    print(
        f"Quantity    : {position.quantity:.6f}"
    )
    print(
        f"Stop Loss   : {position.stop_loss:.2f}"
    )
    print(
        f"Take Profit : {position.take_profit:.2f}"
    )
    print(
        f"Current     : {current_price:.2f}"
    )
    print(
        f"PnL         : {pnl:+.4f}"
    )
    print(
        f"Status      : {status}"
    )


def run_signal_bot() -> None:

    symbol, timeframe, testnet = get_settings()

    print()
    print("=" * 55)
    print("              BYBIT AUTOPILOT")
    print("=" * 55)

    print(
        "Mode        : SAFE / PAPER ONLY"
    )

    print(
        "Environment : "
        + (
            "TESTNET"
            if testnet
            else "MAINNET"
        )
    )

    print(
        f"Symbol      : {symbol}"
    )

    print(
        f"Timeframe   : {timeframe} minutes"
    )

    print(
        "Strategy    : EMA 9/21"
    )

    print()
    print(
        "Paper trading is enabled."
    )
    print(
        "No real trading orders will be placed."
    )
    print(
        "Press Ctrl+C to stop the bot."
    )

    print("=" * 55)

    paper_executor = PaperExecutor(
        os.getenv("PAPER_DB_PATH", "logs/paper_positions.db")
    )
    paper_position = paper_executor.position
    trade_history: list[PaperTrade] = paper_executor.closed_trades()

    previous_signal = None

    account_balance = get_paper_balance()
    stop_loss_percent = get_stop_loss_percent()
    reward_ratio = get_reward_ratio()

    try:

        while True:

            try:

                prices = get_candles(
                    symbol=symbol,
                    interval=timeframe,
                    limit=100,
                    testnet=testnet,
                )

                if len(prices) < 21:

                    print()
                    print(
                        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                        "Not enough candle data."
                    )

                    time.sleep(30)
                    continue

                result = analyze_prices(
                    prices
                )

                fast_ema = result["fast_ema"]
                slow_ema = result["slow_ema"]
                signal = result["signal"]

                last_price = prices[-1]

                now = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                print()
                print("-" * 55)
                print(
                    f"Time         : {now}"
                )
                print(
                    f"Symbol       : {symbol}"
                )
                print(
                    f"Last Price   : {last_price:.2f}"
                )
                print(
                    f"EMA 9        : {fast_ema:.2f}"
                )
                print(
                    f"EMA 21       : {slow_ema:.2f}"
                )
                print(
                    f"Signal       : {signal}"
                )

                # -------------------------------------------------
                # 1. Check existing paper position
                # -------------------------------------------------

                if paper_position is not None:

                    position_status = check_exit(
                        paper_position,
                        last_price,
                    )

                    pnl = calculate_pnl(
                        paper_position,
                        last_price,
                    )

                    print()
                    print(
                        "Paper Position: "
                        f"{paper_position.side}"
                    )

                    print(
                        f"Entry        : "
                        f"{paper_position.entry_price:.2f}"
                    )

                    print(
                        f"Quantity     : "
                        f"{paper_position.quantity:.6f}"
                    )

                    print(
                        f"PnL          : "
                        f"{pnl:+.4f}"
                    )

                    print(
                        f"SL/TP Status : "
                        f"{position_status}"
                    )

                    # -------------------------------------------------
                    # 2. Close on SL / TP
                    # -------------------------------------------------

                    if position_status != "OPEN":

                        trade = paper_executor.close_position(
                            last_price,
                            position_status,
                        )

                        trade_history.append(
                            trade
                        )

                        print()
                        print(
                            "=== PAPER POSITION CLOSED ==="
                        )

                        print(
                            format_paper_trade(
                                trade
                            )
                        )

                        paper_position = None

                    # -------------------------------------------------
                    # 3. Optional signal-change close
                    # -------------------------------------------------

                    elif (
                        signal in {"BUY", "SELL"}
                        and signal != paper_position.side
                    ):

                        trade = paper_executor.close_position(
                            last_price,
                            "MANUAL_CLOSE",
                        )

                        trade_history.append(
                            trade
                        )

                        print()
                        print(
                            "=== PAPER POSITION CLOSED ==="
                        )

                        print(
                            format_paper_trade(
                                trade
                            )
                        )

                        paper_position = None

                # -------------------------------------------------
                # 4. Open new paper position
                # -------------------------------------------------

                if (
                    paper_position is None
                    and signal in {"BUY", "SELL"}
                ):

                    risk_result = calculate_risk(
                        entry=last_price,
                        account_balance=account_balance,
                        stop_loss_percent=stop_loss_percent,
                        reward_ratio=reward_ratio,
                    )

                    stop_loss = risk_result.stop_loss
                    take_profit = risk_result.take_profit

                    if signal == "SELL":

                        stop_loss = (
                            last_price
                            * (
                                1
                                + stop_loss_percent
                                / 100
                            )
                        )

                        take_profit = (
                            last_price
                            * (
                                1
                                - (
                                    stop_loss_percent
                                    * reward_ratio
                                    / 100
                                )
                            )
                        )

                    paper_position = (
                        paper_executor.open_position(
                            signal,
                            last_price,
                            risk_result.position_size,
                            stop_loss,
                            take_profit,
                            symbol,
                            timeframe,
                            "EMA Crossover (9/21)",
                        )
                    )

                    if paper_position:

                        print()
                        print(
                            "=== PAPER POSITION OPENED ==="
                        )

                        print(
                            f"Side        : "
                            f"{paper_position.side}"
                        )

                        print(
                            f"Entry       : "
                            f"{paper_position.entry_price:.2f}"
                        )

                        print(
                            f"Quantity    : "
                            f"{paper_position.quantity:.6f}"
                        )

                        print(
                            f"Stop Loss   : "
                            f"{paper_position.stop_loss:.2f}"
                        )

                        print(
                            f"Take Profit : "
                            f"{paper_position.take_profit:.2f}"
                        )

                        print(
                            f"Risk        : "
                            f"{risk_result.risk_percent:.2f}%"
                        )

                        print(
                            "Execution   : PAPER ONLY"
                        )

                # -------------------------------------------------
                # 5. Summary
                # -------------------------------------------------

                print()
                print(
                    "Mode         : PAPER ONLY"
                )

                if paper_position:

                    print(
                        "Position     : "
                        f"{paper_position.side}"
                    )

                else:

                    print(
                        "Position     : NONE"
                    )

                print(
                    f"Trade History: "
                    f"{len(trade_history)} closed"
                )

                print(
                    "Order        : NOT PLACED"
                )

                print("-" * 55)

                previous_signal = signal

            except Exception as exc:

                print()
                print("=" * 55)
                print("BOT ERROR")
                print("=" * 55)
                print(
                    f"Error: {exc}"
                )
                print(
                    "Retrying..."
                )
                print("=" * 55)

            # Refresh every 30 seconds.
            time.sleep(30)

    except KeyboardInterrupt:

        print()
        print()
        print("=" * 55)
        print("             BOT STOPPED")
        print("=" * 55)

        if paper_position:

            current_price = prices[-1]

            pnl = calculate_pnl(
                paper_position,
                current_price,
            )

            print(
                f"Open Paper Position : "
                f"{paper_position.side}"
            )

            print(
                f"Current PnL         : "
                f"{pnl:+.4f}"
            )

        print(
            f"Closed Trades       : "
            f"{len(trade_history)}"
        )

        print(
            "✓ Paper trading only."
        )

        print(
            "✓ No real trading order was placed."
        )

        paper_executor.close()

        print("=" * 55)


if __name__ == "__main__":
    run_signal_bot()
