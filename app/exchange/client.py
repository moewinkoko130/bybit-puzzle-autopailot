import os
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any, Callable

from pybit.unified_trading import HTTP


class ExchangeAPIError(RuntimeError):
    pass


class ExchangeSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstrumentRules:
    tick_size: Decimal
    qty_step: Decimal
    min_qty: Decimal
    min_notional: Decimal

    def price(self, value: float) -> float:
        decimal_value = Decimal(str(value))
        return float((decimal_value / self.tick_size).to_integral_value(rounding=ROUND_DOWN) * self.tick_size)

    def quantity(self, value: float) -> float:
        decimal_value = Decimal(str(value))
        return float((decimal_value / self.qty_step).to_integral_value(rounding=ROUND_DOWN) * self.qty_step)


class BybitV5Client:
    TESTNET_ENDPOINT = "https://api-testnet.bybit.com"
    MAINNET_ENDPOINT = "https://api.bybit.com"

    def __init__(
        self,
        testnet: bool,
        api_key: str = "",
        api_secret: str = "",
        session: Any | None = None,
        max_attempts: int = 3,
        backoff: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
        allow_mainnet: bool = False,
    ) -> None:
        self.testnet = testnet
        self.endpoint = self.TESTNET_ENDPOINT if testnet else self.MAINNET_ENDPOINT
        self.session = session or HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )
        self.max_attempts = max(1, max_attempts)
        self.backoff = max(0.0, backoff)
        self.sleep = sleep
        self.allow_mainnet = allow_mainnet
        self._verify_endpoint()

    def _verify_endpoint(self) -> None:
        configured = getattr(self.session, "endpoint", None)
        if configured and configured.rstrip("/") != self.endpoint:
            raise ExchangeSafetyError("Bybit session endpoint does not match environment.")

    def _call(self, method: str, **params: Any) -> dict:
        if method in {"place_order", "cancel_order", "set_trading_stop"}:
            if self.allow_mainnet:
                self._require_mainnet()
            else:
                self._require_testnet()
        for attempt in range(self.max_attempts):
            try:
                response = getattr(self.session, method)(**params)
                code = response.get("retCode", -1)
                if code == 0:
                    return response
                if self._retryable_code(code) and attempt + 1 < self.max_attempts:
                    self.sleep(self.backoff * (2 ** attempt))
                    continue
                raise ExchangeAPIError(f"Bybit API error {code}: {response.get('retMsg')}")
            except ExchangeSafetyError:
                raise
            except ExchangeAPIError:
                raise
            except Exception as exc:
                if attempt + 1 == self.max_attempts:
                    raise ExchangeAPIError(f"Bybit request failed: {exc}") from exc
                self.sleep(self.backoff * (2 ** attempt))
        raise ExchangeAPIError("Bybit request failed after retries.")

    @staticmethod
    def _retryable_code(code: int) -> bool:
        return code in {10006, 10016, 429, 10018}

    def _require_testnet(self) -> None:
        if os.getenv("BYBIT_TESTNET", "true").lower() != "true" or not self.testnet:
            raise ExchangeSafetyError("Order operations require BYBIT_TESTNET=true.")
        self._verify_endpoint()

    def _require_mainnet(self) -> None:
        if os.getenv("BYBIT_TESTNET", "true").lower() != "false" or self.testnet:
            raise ExchangeSafetyError("Mainnet order operations require BYBIT_TESTNET=false.")
        if self.endpoint != self.MAINNET_ENDPOINT:
            raise ExchangeSafetyError("Mainnet endpoint verification failed.")
        self._verify_endpoint()

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> list[float]:
        rows = self._call("get_kline", category="linear", symbol=symbol, interval=interval, limit=limit).get("result", {}).get("list", [])
        return [float(row[4]) for row in reversed(rows)]

    def get_ticker(self, symbol: str) -> float:
        rows = self._call("get_tickers", category="linear", symbol=symbol).get("result", {}).get("list", [])
        if not rows:
            raise ExchangeAPIError("No ticker data returned.")
        return float(rows[0]["lastPrice"])

    def get_instrument_rules(self, symbol: str) -> InstrumentRules:
        info = self._call("get_instruments_info", category="linear", symbol=symbol).get("result", {}).get("list", [])
        if not info:
            raise ExchangeAPIError("No instrument information returned.")
        item = info[0]
        price_filter = item["priceFilter"]
        lot = item["lotSizeFilter"]
        return InstrumentRules(
            tick_size=Decimal(price_filter["tickSize"]),
            qty_step=Decimal(lot["qtyStep"]),
            min_qty=Decimal(lot["minOrderQty"]),
            min_notional=Decimal(lot.get("minNotionalValue", "0")),
        )

    def create_order(self, **params: Any) -> dict:
        return self._call("place_order", category="linear", **params).get("result", {})

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        return self._call("cancel_order", category="linear", symbol=symbol, orderId=order_id).get("result", {})

    def get_positions(self, symbol: str) -> list[dict]:
        return self._call("get_positions", category="linear", symbol=symbol).get("result", {}).get("list", [])

    def get_wallet_balance(self) -> dict:
        return self._call("get_wallet_balance", accountType="UNIFIED")

    def get_open_orders(self, symbol: str) -> list[dict]:
        return self._call("get_open_orders", category="linear", symbol=symbol).get("result", {}).get("list", [])

    def set_trading_stop(self, symbol: str, **params: Any) -> dict:
        return self._call("set_trading_stop", category="linear", symbol=symbol, **params).get("result", {})
