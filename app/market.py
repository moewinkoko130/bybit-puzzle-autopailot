from pybit.unified_trading import HTTP


def get_session(testnet: bool, api_key: str = "", api_secret: str = ""):
    if api_key and api_secret:
        return HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )

    return HTTP(testnet=testnet)


def get_candles(
    symbol: str = "BTCUSDT",
    interval: str = "5",
    limit: int = 100,
    testnet: bool = False,
    api_key: str = "",
    api_secret: str = "",
) -> list[float]:

    session = get_session(
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret,
    )

    response = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit,
    )

    if response.get("retCode") != 0:
        raise RuntimeError(
            f"Bybit API error "
            f"{response.get('retCode')}: "
            f"{response.get('retMsg')}"
        )

    rows = (
        response
        .get("result", {})
        .get("list", [])
    )

    if not rows:
        return []

    # Bybit returns newest candles first.
    rows = list(reversed(rows))

    closes = []

    for row in rows:
        closes.append(float(row[4]))

    return closes


def get_latest_price(
    symbol: str = "BTCUSDT",
    testnet: bool = False,
) -> float:

    session = get_session(
        testnet=testnet,
    )

    response = session.get_tickers(
        category="linear",
        symbol=symbol,
    )

    if response.get("retCode") != 0:
        raise RuntimeError(
            f"Bybit API error "
            f"{response.get('retCode')}: "
            f"{response.get('retMsg')}"
        )

    ticker_list = (
        response
        .get("result", {})
        .get("list", [])
    )

    if not ticker_list:
        raise RuntimeError(
            "No ticker data returned."
        )

    return float(
        ticker_list[0]["lastPrice"]
    )
