import pytest

from app.exchange import (
    BybitV5Client,
    ExchangeAPIError,
    ExchangeSafetyError,
    TestnetExecutor as SandboxExecutor,
    reconcile_positions,
)


class FakeSession:
    __test__ = False
    endpoint = "https://api-testnet.bybit.com"

    def __init__(self, responses=None, failures=0):
        self.responses = list(responses or [])
        self.failures = failures
        self.calls = []

    def place_order(self, **params):
        self.calls.append(("place_order", params))
        if self.failures:
            self.failures -= 1
            raise TimeoutError("temporary network failure")
        return self.responses.pop(0) if self.responses else {"retCode": 0, "result": {"orderId": "abc"}}

    def get_kline(self, **params):
        return {"retCode": 0, "result": {"list": [["0", "0", "0", "0", "101"]]}}

    def get_instruments_info(self, **params):
        return {"retCode": 0, "result": {"list": [{"priceFilter": {"tickSize": "0.1"}, "lotSizeFilter": {"qtyStep": "0.01", "minOrderQty": "0.01", "minNotionalValue": "5"}}]}}


def test_testnet_order_routes_through_v5_client(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "true")
    session = FakeSession()
    executor = SandboxExecutor(BybitV5Client(True, session=session))
    result = executor.submit("BTCUSDT", "BUY", 1.25, 100.1)
    assert result.order_id == "abc"
    assert session.calls[0][1]["category"] == "linear"
    assert session.calls[0][1]["orderType"] == "Limit"


def test_mutating_client_retries_network_failure(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "true")
    session = FakeSession(failures=2)
    client = BybitV5Client(True, session=session, backoff=1, sleep=lambda _: None)
    assert client.create_order(symbol="BTCUSDT", side="BUY", orderType="Market", qty="1")["orderId"] == "abc"


def test_rate_limit_response_is_retried(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "true")
    session = FakeSession(responses=[{"retCode": 10006, "retMsg": "rate limit"}, {"retCode": 0, "result": {"orderId": "abc"}}])
    client = BybitV5Client(True, session=session, sleep=lambda _: None)
    assert client.create_order(symbol="BTCUSDT", side="BUY", orderType="Market", qty="1")["orderId"] == "abc"


def test_mainnet_order_is_rejected(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "false")
    session = FakeSession()
    session.endpoint = "https://api.bybit.com"
    client = BybitV5Client(False, session=session)
    with pytest.raises(ExchangeSafetyError):
        client.create_order(symbol="BTCUSDT", side="BUY", orderType="Market", qty="1")


def test_instrument_rules_round_down_values(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "true")
    rules = BybitV5Client(True, session=FakeSession()).get_instrument_rules("BTCUSDT")
    assert rules.price(100.19) == 100.1
    assert rules.quantity(1.239) == 1.23


def test_reconciliation_reports_missing_and_quantity_drift():
    mismatches = reconcile_positions(
        [{"side": "Buy", "size": "2"}, {"side": "Sell", "size": "1"}],
        [{"side": "Buy", "size": "1"}, {"side": "None", "size": "0"}],
    )
    assert any(item.reason == "position_quantity_or_side_mismatch" for item in mismatches)
    assert any(item.reason == "missing_remote_position" for item in mismatches)
    assert any(item.reason == "missing_local_position" for item in mismatches)


def test_order_reconciliation_reports_partial_fill():
    from app.exchange import reconcile_orders

    mismatches = reconcile_orders(
        [{"orderId": "abc", "orderStatus": "New", "cumExecQty": "0"}],
        [{"orderId": "abc", "orderStatus": "PartiallyFilled", "cumExecQty": "0.5"}],
    )
    assert mismatches[0].reason == "order_status_or_fill_mismatch"
