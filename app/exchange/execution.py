import os
from dataclasses import dataclass
from typing import Any

from app.exchange.client import BybitV5Client, ExchangeSafetyError
from app.exchange.reconciliation import ReconciliationMismatch, reconcile_orders, reconcile_positions


@dataclass(frozen=True)
class ExecutionResult:
    order_id: str
    status: str
    raw: dict


class TestnetExecutor:
    def __init__(self, client: BybitV5Client) -> None:
        if not client.testnet or os.getenv("BYBIT_TESTNET", "true").lower() != "true":
            raise ExchangeSafetyError("TestnetExecutor requires BYBIT_TESTNET=true.")
        if client.endpoint != BybitV5Client.TESTNET_ENDPOINT:
            raise ExchangeSafetyError("TestnetExecutor received a non-testnet endpoint.")
        self.client = client

    def submit(self, symbol: str, side: str, quantity: float, price: float | None = None, **params: Any) -> ExecutionResult:
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
        return ExecutionResult(result.get("orderId", ""), result.get("orderStatus", "UNKNOWN"), result)

    def cancel(self, symbol: str, order_id: str) -> dict:
        return self.client.cancel_order(symbol, order_id)

    def positions(self, symbol: str) -> list[dict]:
        return self.client.get_positions(symbol)

    def trading_stop(self, symbol: str, **params: Any) -> dict:
        return self.client.set_trading_stop(symbol, **params)


class TradingEngine:
    def __init__(self, executor: TestnetExecutor) -> None:
        self.executor = executor

    def execute_signal(self, symbol: str, signal: str, quantity: float, price: float | None = None, **params: Any) -> ExecutionResult:
        if signal.upper() not in {"BUY", "SELL"}:
            raise ValueError("Signal must be BUY or SELL.")
        return self.executor.submit(symbol, signal, quantity, price, **params)

    def reconcile(self, local_positions: list[dict], symbol: str) -> list[ReconciliationMismatch]:
        return reconcile_positions(local_positions, self.executor.positions(symbol))

    def reconcile_orders(self, local_orders: list[dict], symbol: str) -> list[ReconciliationMismatch]:
        return reconcile_orders(local_orders, self.executor.client.get_open_orders(symbol))
