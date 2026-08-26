import os
from typing import Any

from app.exchange.client import BybitV5Client, ExchangeSafetyError
from app.exchange.execution import ExecutionResult
from app.exchange.security import LivePreflight, run_live_preflight


class LiveExecutor:
    """Production executor requiring completed confirmation and preflight."""

    def __init__(
        self,
        client: BybitV5Client,
        preflight: LivePreflight,
    ) -> None:
        if not isinstance(preflight, LivePreflight) or not preflight.confirmed:
            raise ExchangeSafetyError("LiveExecutor requires completed live preflight.")
        if client.testnet or client.endpoint != BybitV5Client.MAINNET_ENDPOINT:
            raise ExchangeSafetyError("LiveExecutor requires the mainnet endpoint.")
        if os.getenv("BYBIT_TESTNET", "true").lower() != "false":
            raise ExchangeSafetyError("LiveExecutor requires BYBIT_TESTNET=false.")
        self.client = client
        self.preflight = preflight

    @classmethod
    def create(
        cls,
        api_key: str,
        api_secret: str,
        symbol: str,
        confirmed: bool,
        **client_options: Any,
    ) -> "LiveExecutor":
        if os.getenv("BYBIT_TESTNET", "true").lower() != "false":
            raise ExchangeSafetyError("Live mode requires BYBIT_TESTNET=false.")
        if not confirmed:
            raise ExchangeSafetyError("Live confirmation was not completed.")
        if not api_key.strip() or not api_secret.strip():
            raise ExchangeSafetyError("Live API credentials are required.")
        client = BybitV5Client(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
            allow_mainnet=True,
            **client_options,
        )
        preflight = run_live_preflight(
            client, symbol, api_key, api_secret, confirmed
        )
        return cls(client, preflight)

    def submit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
        **params: Any,
    ) -> ExecutionResult:
        rules = self.client.get_instrument_rules(symbol)
        normalized_quantity = rules.quantity(quantity)
        if normalized_quantity < float(rules.min_qty):
            raise ValueError("Order quantity is below the exchange minimum.")
        if price is not None:
            price = rules.price(price)
            if price * normalized_quantity < float(rules.min_notional):
                raise ValueError("Order value is below the exchange minimum.")
        request = {
            "symbol": symbol,
            "side": side.upper(),
            "orderType": "Limit" if price is not None else "Market",
            "qty": str(normalized_quantity),
            **params,
        }
        if price is not None:
            request["price"] = str(price)
            request.setdefault("timeInForce", "GTC")
        result = self.client.create_order(**request)
        return ExecutionResult(
            result.get("orderId", ""),
            result.get("orderStatus", "UNKNOWN"),
            result,
        )
