import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from pybit.unified_trading import HTTP

from app.strategy import (
    ema_signal,
    strategy_status,
)

from app.live_analysis import (
    live_strategy_analysis,
)

from app.bot import run_signal_bot
from app.risk import calculate_risk, risk_status


ENV_FILE = Path(".env")

load_dotenv(ENV_FILE)


def mask_secret(
    value: str,
    show_chars: int = 4,
) -> str:

    if not value:
        return "Not configured"

    if len(value) <= show_chars * 2:
        return "*" * len(value)

    return (
        value[:show_chars]
        + "*" * (
            len(value)
            - show_chars * 2
        )
        + value[-show_chars:]
    )


def save_env_value(
    key: str,
    value: str,
) -> None:

    lines = []

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()

    updated = False
    new_lines = []

    for line in lines:

        if line.startswith(f"{key}="):

            new_lines.append(
                f"{key}={value}"
            )

            updated = True

        else:

            new_lines.append(line)

    if not updated:

        new_lines.append(
            f"{key}={value}"
        )

    ENV_FILE.write_text(
        "\n".join(new_lines) + "\n"
    )


def get_session():

    api_key = os.getenv(
        "BYBIT_API_KEY",
        "",
    ).strip()

    api_secret = os.getenv(
        "BYBIT_API_SECRET",
        "",
    ).strip()

    testnet = (
        os.getenv(
            "BYBIT_TESTNET",
            "true",
        ).lower()
        == "true"
    )

    if not api_key or not api_secret:
        return None

    return HTTP(
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret,
    )


def configure_api() -> None:

    print()
    print("=" * 45)
    print("        BYBIT API CONFIGURATION")
    print("=" * 45)

    api_key = input(
        "Bybit API Key: "
    ).strip()

    api_secret = getpass(
        "Bybit API Secret: "
    ).strip()

    if not api_key or not api_secret:

        print()
        print(
            "API Key and API Secret "
            "cannot be empty."
        )

        return

    save_env_value(
        "BYBIT_API_KEY",
        api_key,
    )

    save_env_value(
        "BYBIT_API_SECRET",
        api_secret,
    )

    os.environ[
        "BYBIT_API_KEY"
    ] = api_key

    os.environ[
        "BYBIT_API_SECRET"
    ] = api_secret

    print()
    print(
        "✓ API credentials saved to .env"
    )

    print(
        "✓ API Secret is hidden."
    )

    print(
        "✓ No trading order was placed."
    )


def show_status() -> None:

    api_key = os.getenv(
        "BYBIT_API_KEY",
        "",
    ).strip()

    api_secret = os.getenv(
        "BYBIT_API_SECRET",
        "",
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
    print("           CONFIGURATION STATUS")
    print("=" * 45)

    print(
        f"API Key     : "
        f"{mask_secret(api_key)}"
    )

    print(
        "API Secret  : "
        + (
            "********"
            if api_secret
            else "Not configured"
        )
    )

    print(
        f"Testnet     : "
        f"{'ON' if testnet else 'OFF'}"
    )

    print(
        "Trading Mode: SAFE / DRY RUN"
    )

    print("=" * 45)


def test_api_connection() -> None:

    session = get_session()

    print()
    print("=" * 45)
    print("          API CONNECTION TEST")
    print("=" * 45)

    if session is None:

        print(
            "✗ API credentials "
            "are not configured."
        )

        print(
            "Use option 1 first."
        )

        return

    testnet = (
        os.getenv(
            "BYBIT_TESTNET",
            "true",
        ).lower()
        == "true"
    )

    print(
        "Environment: "
        + (
            "TESTNET"
            if testnet
            else "MAINNET"
        )
    )

    print(
        "Connecting to Bybit..."
    )

    print()

    try:

        response = (
            session.get_wallet_balance(
                accountType="UNIFIED"
            )
        )

        if response.get(
            "retCode"
        ) == 0:

            print(
                "✓ API connection successful."
            )

            print(
                "✓ Authentication successful."
            )

            print(
                "✓ No trading order was placed."
            )

        else:

            print(
                "✗ Bybit API returned an error."
            )

            print(
                f"Code: "
                f"{response.get('retCode')}"
            )

            print(
                f"Message: "
                f"{response.get('retMsg')}"
            )

    except Exception as exc:

        print(
            "✗ Connection failed."
        )

        print(
            f"Error: {exc}"
        )

    print("=" * 45)


def account_balance() -> None:

    session = get_session()

    print()
    print("=" * 45)
    print("             ACCOUNT BALANCE")
    print("=" * 45)

    if session is None:

        print(
            "✗ API credentials "
            "are not configured."
        )

        print(
            "Use option 1 first."
        )

        return

    try:

        response = (
            session.get_wallet_balance(
                accountType="UNIFIED"
            )
        )

        if response.get(
            "retCode"
        ) != 0:

            print(
                "✗ Failed to retrieve balance."
            )

            print(
                f"Code: "
                f"{response.get('retCode')}"
            )

            print(
                f"Message: "
                f"{response.get('retMsg')}"
            )

            return

        accounts = (
            response
            .get("result", {})
            .get("list", [])
        )

        if not accounts:

            print(
                "No account data returned."
            )

            return

        account = accounts[0]

        print(
            f"Account Type : "
            f"{account.get('accountType')}"
        )

        print(
            f"Total Equity : "
            f"{account.get('totalEquity')}"
        )

        print(
            f"Total Wallet : "
            f"{account.get('totalWalletBalance')}"
        )

        print(
            f"Available    : "
            f"{account.get('totalAvailableBalance')}"
        )

        coins = account.get(
            "coin",
            [],
        )

        if coins:

            print()
            print(
                "Coin Balances:"
            )

            print("-" * 45)

            for coin in coins:

                wallet_balance = coin.get(
                    "walletBalance",
                    "0",
                )

                if wallet_balance != "0":

                    print(
                        f"{coin.get('coin')}: "
                        f"{wallet_balance}"
                    )

        print()

        print(
            "✓ Balance retrieved successfully."
        )

        print(
            "✓ Read-only request."
        )

        print(
            "✓ No order was placed."
        )

    except Exception as exc:

        print(
            "✗ Failed to retrieve "
            "account balance."
        )

        print(
            f"Error: {exc}"
        )

    print("=" * 45)


def market_price() -> None:

    symbol = os.getenv(
        "BYBIT_SYMBOL",
        "BTCUSDT",
    ).strip().upper()

    print()
    print("=" * 45)
    print("              MARKET PRICE")
    print("=" * 45)

    print(
        f"Symbol: {symbol}"
    )

    print(
        "Fetching latest price..."
    )

    try:

        testnet = (
            os.getenv(
                "BYBIT_TESTNET",
                "true",
            ).lower()
            == "true"
        )

        session = HTTP(
            testnet=testnet
        )

        response = session.get_tickers(
            category="linear",
            symbol=symbol,
        )

        if response.get(
            "retCode"
        ) != 0:

            print(
                "✗ Failed to retrieve "
                "market price."
            )

            print(
                f"Code: "
                f"{response.get('retCode')}"
            )

            print(
                f"Message: "
                f"{response.get('retMsg')}"
            )

            return

        ticker_list = (
            response
            .get("result", {})
            .get("list", [])
        )

        if not ticker_list:

            print(
                "No market data returned."
            )

            return

        ticker = ticker_list[0]

        print()

        print(
            f"Symbol       : "
            f"{ticker.get('symbol')}"
        )

        print(
            f"Last Price   : "
            f"{ticker.get('lastPrice')}"
        )

        print(
            f"24h Change % : "
            f"{ticker.get('price24hPcnt')}"
        )

        print(
            f"24h High     : "
            f"{ticker.get('highPrice24h')}"
        )

        print(
            f"24h Low      : "
            f"{ticker.get('lowPrice24h')}"
        )

        print()

        print(
            "✓ Market data retrieved."
        )

        print(
            "✓ No trading order was placed."
        )

    except Exception as exc:

        print(
            "✗ Failed to retrieve "
            "market price."
        )

        print(
            f"Error: {exc}"
        )

    print("=" * 45)


def environment_settings() -> None:

    print()
    print(
        "=== TESTNET / MAINNET SETTINGS ==="
    )

    print()
    print("1. Testnet")
    print("2. Mainnet")
    print("3. Back")

    choice = input(
        "Choose an option: "
    ).strip()

    if choice == "1":

        save_env_value(
            "BYBIT_TESTNET",
            "true",
        )

        os.environ[
            "BYBIT_TESTNET"
        ] = "true"

        print(
            "✓ Testnet enabled."
        )

    elif choice == "2":

        save_env_value(
            "BYBIT_TESTNET",
            "false",
        )

        os.environ[
            "BYBIT_TESTNET"
        ] = "false"

        print(
            "✓ Mainnet enabled."
        )

        print(
            "Trading remains SAFE / DRY RUN."
        )

    elif choice == "3":

        return

    else:

        print(
            "Invalid option."
        )


def trading_mode() -> None:

    print()
    print("=== TRADING MODE ===")
    print()
    print("1. SAFE / DRY RUN")
    print("2. LIVE ORDERS (disabled)")
    print("3. Back")

    choice = input(
        "Choose an option: "
    ).strip()

    if choice == "1":

        print(
            "✓ SAFE / DRY RUN selected."
        )

        print(
            "No trading orders will be placed."
        )

    elif choice == "2":

        print(
            "LIVE ORDERS are disabled."
        )

    elif choice == "3":

        return

    else:

        print(
            "Invalid option."
        )


def market_settings() -> None:

    print()
    print("=== MARKET SETTINGS ===")
    print()
    print("1. Symbol")
    print("2. Timeframe")
    print("3. Back")

    choice = input(
        "Choose an option: "
    ).strip()

    if choice == "1":

        symbol = input(
            "Enter symbol "
            "(example: BTCUSDT): "
        ).strip().upper()

        if symbol:

            save_env_value(
                "BYBIT_SYMBOL",
                symbol,
            )

            os.environ[
                "BYBIT_SYMBOL"
            ] = symbol

            print(
                f"✓ Symbol saved: {symbol}"
            )

        else:

            print(
                "Symbol cannot be empty."
            )

    elif choice == "2":

        timeframe = input(
            "Enter timeframe "
            "(example: 1, 5, 15, 60): "
        ).strip()

        if timeframe.isdigit():

            save_env_value(
                "BYBIT_TIMEFRAME",
                timeframe,
            )

            os.environ[
                "BYBIT_TIMEFRAME"
            ] = timeframe

            print(
                f"✓ Timeframe saved: "
                f"{timeframe} minutes"
            )

        else:

            print(
                "Timeframe must be numeric."
            )

    elif choice == "3":

        return

    else:

        print(
            "Invalid option."
        )


def strategy_settings() -> None:

    print()
    print("=== STRATEGY SETTINGS ===")
    print()
    print("1. EMA Crossover")
    print("2. RSI")
    print("3. Strategy status")
    print("4. Test Strategy")
    print("5. Live Market Analysis")
    print("6. Back")

    choice = input(
        "Choose an option: "
    ).strip()

    if choice == "1":

        print()
        print(
            "=== EMA CROSSOVER ==="
        )

        print(
            "Fast EMA : 9"
        )

        print(
            "Slow EMA : 21"
        )

        print(
            "Mode     : SIGNAL ONLY"
        )

    elif choice == "2":

        print()
        print(
            "RSI strategy is "
            "not active yet."
        )

    elif choice == "3":

        print()

        print(
            "Strategy Engine: "
            f"{strategy_status()}"
        )

        print(
            "Mode: SAFE / SIGNAL ONLY"
        )

    elif choice == "4":

        prices = [
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

        signal = ema_signal(
            prices
        )

        print()
        print(
            "=== STRATEGY TEST ==="
        )

        print(
            "Fast EMA : 9"
        )

        print(
            "Slow EMA : 21"
        )

        print(
            f"Signal   : {signal}"
        )

        print()

        print(
            "✓ Strategy calculation "
            "completed."
        )

        print(
            "✓ No trading order was placed."
        )

    elif choice == "5":

        live_strategy_analysis()

    elif choice == "6":

        return

    else:

        print(
            "Invalid option."
        )


def risk_management() -> None:

    while True:

        print()
        print("=== RISK MANAGEMENT ===")
        print()
        print("1. Max Risk Per Trade")
        print("2. Stop Loss Settings")
        print("3. Take Profit Settings")
        print("4. Position Size Calculator")
        print("5. Risk Status")
        print("6. Back")

        choice = input(
            "Choose an option: "
        ).strip()

        if choice == "1":

            risk = input(
                "Enter maximum risk percentage: "
            ).strip()

            try:

                value = float(risk)

                if 0 < value <= 100:

                    save_env_value(
                        "MAX_RISK_PERCENT",
                        str(value),
                    )

                    os.environ[
                        "MAX_RISK_PERCENT"
                    ] = str(value)

                    print()
                    print(
                        f"✓ Max risk saved: "
                        f"{value}%"
                    )

                else:

                    print()
                    print(
                        "Risk must be between 0 and 100."
                    )

            except ValueError:

                print()
                print(
                    "Please enter a valid number."
                )

        elif choice == "2":

            stop_loss = input(
                "Enter stop-loss percentage "
                "(example: 1): "
            ).strip()

            try:

                value = float(stop_loss)

                if value <= 0:

                    print(
                        "Stop-loss must be greater than zero."
                    )
                    continue

                if value > 100:

                    print(
                        "Stop-loss cannot exceed 100%."
                    )
                    continue

                save_env_value(
                    "PAPER_STOP_LOSS_PERCENT",
                    str(value),
                )

                os.environ[
                    "PAPER_STOP_LOSS_PERCENT"
                ] = str(value)

                print()
                print(
                    f"✓ Stop-loss saved: {value}%"
                )

                print(
                    "✓ PAPER ONLY"
                )

            except ValueError:

                print(
                    "Please enter a valid number."
                )

        elif choice == "3":

            reward = input(
                "Enter reward ratio "
                "(example: 2 for 1:2): "
            ).strip()

            try:

                value = float(reward)

                if value <= 0:

                    print(
                        "Reward ratio must be greater than zero."
                    )
                    continue

                save_env_value(
                    "PAPER_REWARD_RATIO",
                    str(value),
                )

                os.environ[
                    "PAPER_REWARD_RATIO"
                ] = str(value)

                print()
                print(
                    f"✓ Reward ratio saved: 1:{value}"
                )

                print(
                    "✓ PAPER ONLY"
                )

            except ValueError:

                print(
                    "Please enter a valid number."
                )

        elif choice == "4":

            print()
            print("=== POSITION SIZE CALCULATOR ===")
            print()

            balance_input = input(
                "Account balance: "
            ).strip()

            entry_input = input(
                "Entry price: "
            ).strip()

            try:

                balance = float(balance_input)
                entry = float(entry_input)

                stop_loss_percent = float(
                    os.getenv(
                        "PAPER_STOP_LOSS_PERCENT",
                        "1.0",
                    )
                )

                reward_ratio = float(
                    os.getenv(
                        "PAPER_REWARD_RATIO",
                        "2.0",
                    )
                )

                result = calculate_risk(
                    entry=entry,
                    account_balance=balance,
                    stop_loss_percent=stop_loss_percent,
                    reward_ratio=reward_ratio,
                )

                print()
                print("-" * 45)
                print(
                    f"Account Balance : "
                    f"{balance:.2f}"
                )
                print(
                    f"Risk Percent    : "
                    f"{result.risk_percent:.2f}%"
                )
                print(
                    f"Risk Amount     : "
                    f"{result.risk_amount:.2f}"
                )
                print(
                    f"Entry Price     : "
                    f"{result.entry:.2f}"
                )
                print(
                    f"Stop Loss       : "
                    f"{result.stop_loss:.2f}"
                )
                print(
                    f"Take Profit     : "
                    f"{result.take_profit:.2f}"
                )
                print(
                    f"Position Size   : "
                    f"{result.position_size:.6f}"
                )
                print("-" * 45)
                print()
                print("✓ Risk calculation completed.")
                print("✓ PAPER ONLY")
                print("✓ No trading order was placed.")

            except ValueError:

                print()
                print(
                    "Please enter valid numeric values."
                )

            except Exception as exc:

                print()
                print(
                    f"✗ Risk calculation failed: {exc}"
                )

        elif choice == "5":

            risk = os.getenv(
                "MAX_RISK_PERCENT",
                "1.0",
            )

            stop_loss = os.getenv(
                "PAPER_STOP_LOSS_PERCENT",
                "1.0",
            )

            reward_ratio = os.getenv(
                "PAPER_REWARD_RATIO",
                "2.0",
            )

            print()
            print("=== RISK STATUS ===")
            print()
            print(
                f"Max Risk Per Trade : {risk}%"
            )
            print(
                f"Stop Loss          : {stop_loss}%"
            )
            print(
                f"Reward Ratio       : 1:{reward_ratio}"
            )
            print(
                "Execution Mode     : PAPER ONLY"
            )
            print()
            print(
                f"Status             : {risk_status()}"
            )

        elif choice == "6":

            return

        else:

            print()
            print(
                "Invalid option. Please choose 1-6."
            )

def paper_performance() -> None:

    print()
    print("=" * 45)
    print("          PAPER PERFORMANCE")
    print("=" * 45)
    print()
    print("No closed paper trades in current menu session.")
    print()
    print("Persistent trade history will be connected")
    print("to the paper bot in the next step.")
    print()
    print("✓ PAPER ONLY")
    print("✓ No real trading order was placed.")
    print("=" * 45)


def run_bot() -> None:

    run_signal_bot()


def show_menu() -> None:

    while True:

        print()
        print("=" * 45)
        print("             BYBIT AUTOPILOT")
        print("=" * 45)

        print(
            "1. Configure Bybit API"
        )

        print(
            "2. View Configuration"
        )

        print(
            "3. Testnet / Mainnet"
        )

        print(
            "4. Trading Mode"
        )

        print(
            "5. Market Settings"
        )

        print(
            "6. Test API Connection"
        )

        print(
            "7. Account Balance"
        )

        print(
            "8. Market Price"
        )

        print(
            "9. Strategy Settings"
        )

        print(
            "10. Risk Management"
        )

        print(
            "11. Run Bot"
        )

        print(
            "12. Exit"
        )

        print("=" * 45)

        choice = input(
            "Choose an option: "
        ).strip()

        if choice == "1":

            configure_api()

        elif choice == "2":

            show_status()

        elif choice == "3":

            environment_settings()

        elif choice == "4":

            trading_mode()

        elif choice == "5":

            market_settings()

        elif choice == "6":

            test_api_connection()

        elif choice == "7":

            account_balance()

        elif choice == "8":

            market_price()

        elif choice == "9":

            strategy_settings()

        elif choice == "10":

            risk_management()

        elif choice == "11":

            run_bot()

        elif choice == "13":

            paper_performance()

        elif choice == "12":

            print()
            print(
                "Exiting BYBIT AUTOPILOT."
            )

            break

        else:

            print()
            print(
                "Invalid option. "
                "Please choose 1-12."
            )


def main() -> None:

    show_menu()


if __name__ == "__main__":

    main()


