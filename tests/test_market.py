import pytest

from app.market import BybitAdapter, MarketDataError


class FakeSession:
    def __init__(self, responses, errors=None):
        self.responses = responses
        self.errors = errors or {}
        self.calls = []

    def _reply(self, name, **params):
        self.calls.append((name, params))
        error = self.errors.pop(name, None)
        if error is not None:
            raise error
        return self.responses[name]

    def get_kline(self, **params):
        return self._reply("get_kline", **params)

    def get_tickers(self, **params):
        return self._reply("get_tickers", **params)

    def get_instruments_info(self, **params):
        return self._reply("get_instruments_info", **params)


def test_adapter_reads_candles_ticker_and_symbol_info_without_order_calls():
    session = FakeSession({
        "get_kline": {"retCode": 0, "result": {"list": [["", "", "", "", "101"], ["", "", "", "", "100"]]}},
        "get_tickers": {"retCode": 0, "result": {"list": [{"lastPrice": "102.5"}]}},
        "get_instruments_info": {"retCode": 0, "result": {"list": [{
            "symbol": "BTCUSDT",
            "priceFilter": {"tickSize": "0.1"},
            "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5"},
        }]}},
    })
    adapter = BybitAdapter(session=session, sleeper=lambda delay: None)

    assert adapter.get_candles() == [100.0, 101.0]
    assert adapter.get_latest_price() == 102.5
    info = adapter.get_symbol_info()
    assert info.tick_size == 0.1
    assert info.quantity_step == 0.001
    assert info.minimum_quantity == 0.001
    assert info.minimum_order_value == 5
    assert [call[0] for call in session.calls] == [
        "get_kline", "get_tickers", "get_instruments_info"
    ]


def test_adapter_retries_network_failures_with_exponential_backoff():
    session = FakeSession(
        {"get_tickers": {"retCode": 0, "result": {"list": [{"lastPrice": "102.5"}]}}},
        {"get_tickers": TimeoutError("temporary")},
    )
    delays = []
    adapter = BybitAdapter(session=session, max_retries=2, backoff_factor=1, sleeper=delays.append)

    assert adapter.get_latest_price() == 102.5
    assert delays == [1]
    assert len(session.calls) == 2


def test_adapter_retries_rate_limit_response():
    session = FakeSession({"get_tickers": {"retCode": 10006, "retMsg": "rate limit"}})
    delays = []
    adapter = BybitAdapter(session=session, max_retries=1, sleeper=delays.append)

    with pytest.raises(MarketDataError, match="10006"):
        adapter.get_latest_price()
    assert delays == [0.5]
    assert len(session.calls) == 2


def test_adapter_rejects_malformed_market_data():
    session = FakeSession({"get_tickers": {"retCode": 0, "result": {"list": [{"lastPrice": "bad"}]}}})
    adapter = BybitAdapter(session=session, sleeper=lambda delay: None)

    with pytest.raises(MarketDataError, match="malformed ticker"):
        adapter.get_latest_price()