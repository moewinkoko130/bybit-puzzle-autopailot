import time
from dataclasses import dataclass
from typing import Any, Callable

from pybit.exceptions import FailedRequestError
from pybit.unified_trading import HTTP


class MarketDataError(RuntimeError):
    """Raised when Bybit market data cannot be read or validated."""


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    tick_size: float
    quantity_step: float
    minimum_quantity: float
    minimum_order_value: float


def get_session(testnet: bool, api_key: str = "", api_secret: str = ""):
    if api_key and api_secret:
        return HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )

    return HTTP(testnet=testnet)


class BybitAdapter:
    """Read-only Bybit market-data adapter."""

    def __init__(
        self,
        testnet: bool = True,
        api_key: str = "",
        api_secret: str = "",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        sleeper: Callable[[float], None] = time.sleep,
        session: Any | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative.")
        if backoff_factor < 0:
            raise ValueError("backoff_factor cannot be negative.")
        self.session = session or get_session(testnet, api_key, api_secret)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.sleeper = sleeper

    @staticmethod
    def _is_rate_limited(response: dict[str, Any]) -> bool:
        return str(response.get("retCode")) in {"10006", "429"}

    def _request(self, method_name: str, **params: Any) -> dict[str, Any]:
        method = getattr(self.session, method_name)
        for attempt in range(self.max_retries + 1):
            try:
                response = method(**params)
                if not isinstance(response, dict):
                    raise MarketDataError("Bybit returned a malformed response.")
                if self._is_rate_limited(response) and attempt < self.max_retries:
                    self.sleeper(self.backoff_factor * (2 ** attempt))
                    continue
                if response.get("retCode") != 0:
                    raise MarketDataError(
                        f"Bybit API error {response.get('retCode')}: "
                        f"{response.get('retMsg')}"
                    )
                return response
            except MarketDataError:
                raise
            except (FailedRequestError, TimeoutError, ConnectionError, OSError) as error:
                if attempt == self.max_retries:
                    raise MarketDataError("Unable to read Bybit market data.") from error
                self.sleeper(self.backoff_factor * (2 ** attempt))
        raise MarketDataError("Unable to read Bybit market data.")

    def get_candles(
        self, symbol: str = "BTCUSDT", interval: str = "5", limit: int = 100
    ) -> list[float]:
        response = self._request(
            "get_kline", category="linear", symbol=symbol, interval=interval, limit=limit
        )
        rows = response.get("result", {}).get("list", [])
        if not isinstance(rows, list):
            raise MarketDataError("Bybit returned malformed candle data.")
        try:
            return [float(row[4]) for row in reversed(rows)]
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise MarketDataError("Bybit returned malformed candle data.") from error

    def get_ticker(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        response = self._request("get_tickers", category="linear", symbol=symbol)
        ticker_list = response.get("result", {}).get("list", [])
        if not isinstance(ticker_list, list) or not ticker_list or not isinstance(ticker_list[0], dict):
            raise MarketDataError("No ticker data returned.")
        return ticker_list[0]

    def get_latest_price(self, symbol: str = "BTCUSDT") -> float:
        try:
            return float(self.get_ticker(symbol)["lastPrice"])
        except (KeyError, TypeError, ValueError) as error:
            raise MarketDataError("Bybit returned malformed ticker data.") from error

    def get_symbol_info(self, symbol: str = "BTCUSDT") -> SymbolInfo:
        response = self._request(
            "get_instruments_info", category="linear", symbol=symbol
        )
        instruments = response.get("result", {}).get("list", [])
        if not isinstance(instruments, list) or not instruments or not isinstance(instruments[0], dict):
            raise MarketDataError("No symbol information returned.")
        try:
            instrument = instruments[0]
            price_filter = instrument["priceFilter"]
            lot_filter = instrument["lotSizeFilter"]
            minimum_order_value = lot_filter.get(
                "minNotionalValue", lot_filter.get("minOrderValue", 0)
            )
            return SymbolInfo(
                symbol=instrument["symbol"],
                tick_size=float(price_filter["tickSize"]),
                quantity_step=float(lot_filter["qtyStep"]),
                minimum_quantity=float(lot_filter["minOrderQty"]),
                minimum_order_value=float(minimum_order_value),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise MarketDataError("Bybit returned malformed symbol information.") from error


def get_candles(
    symbol: str = "BTCUSDT",
    interval: str = "5",
    limit: int = 100,
    testnet: bool = False,
    api_key: str = "",
    api_secret: str = "",
) -> list[float]:
    return BybitAdapter(
        testnet=testnet, api_key=api_key, api_secret=api_secret
    ).get_candles(symbol, interval, limit)


def get_latest_price(
    symbol: str = "BTCUSDT",
    testnet: bool = False,
) -> float:
    return BybitAdapter(testnet=testnet).get_latest_price(symbol)
