import pytest

from app.exchange import BybitV5Client, ExchangeSafetyError, LiveExecutor, LivePreflightError, confirm_live_trading, run_live_preflight


class LiveSession:
    endpoint = "https://api.bybit.com"

    def get_instruments_info(self, **params):
        return {"retCode": 0, "result": {"list": [{"priceFilter": {"tickSize": "0.1"}, "lotSizeFilter": {"qtyStep": "0.01", "minOrderQty": "0.01"}}]}}

    def get_wallet_balance(self, **params):
        return {"retCode": 0, "result": {"list": [{"totalEquity": "1000"}]}}


class BrokenAccountSession(LiveSession):
    def get_wallet_balance(self, **params):
        return {"retCode": 10001, "retMsg": "account unavailable"}


def live_client(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "false")
    return BybitV5Client(False, session=LiveSession(), allow_mainnet=True)


def test_confirmation_requires_exact_phrase_and_final_yes():
    answers = iter(["enable live trading", "YES"])
    assert not confirm_live_trading(input_fn=lambda _: next(answers), output_fn=lambda _: None)
    answers = iter(["ENABLE LIVE TRADING", "yes"])
    assert confirm_live_trading(input_fn=lambda _: next(answers), output_fn=lambda _: None)


def test_preflight_hard_blocks_missing_credentials(monkeypatch):
    client = live_client(monkeypatch)
    with pytest.raises(LivePreflightError, match="credentials"):
        run_live_preflight(client, "BTCUSDT", "", "secret", True)


def test_preflight_hard_blocks_invalid_risk(monkeypatch):
    client = live_client(monkeypatch)
    monkeypatch.setenv("MAX_RISK_PERCENT", "6")
    with pytest.raises(LivePreflightError, match="risk"):
        run_live_preflight(client, "BTCUSDT", "key", "secret", True)


def test_preflight_hard_blocks_malformed_risk(monkeypatch):
    client = live_client(monkeypatch)
    monkeypatch.setenv("MAX_RISK_PERCENT", "not-a-number")
    with pytest.raises(LivePreflightError, match="risk"):
        run_live_preflight(client, "BTCUSDT", "key", "secret", True)


def test_preflight_hard_blocks_account_query_failure(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "false")
    client = BybitV5Client(False, session=BrokenAccountSession(), allow_mainnet=True)
    with pytest.raises(LivePreflightError, match="preflight"):
        run_live_preflight(client, "BTCUSDT", "key", "secret", True)


def test_live_executor_requires_preflight(monkeypatch):
    client = live_client(monkeypatch)
    with pytest.raises(ExchangeSafetyError, match="preflight"):
        LiveExecutor(client, None)


def test_live_client_cannot_mutate_without_explicit_environment(monkeypatch):
    monkeypatch.setenv("BYBIT_TESTNET", "true")
    client = BybitV5Client(False, session=LiveSession(), allow_mainnet=True)
    with pytest.raises(ExchangeSafetyError):
        client.create_order(symbol="BTCUSDT", side="Buy", orderType="Market", qty="1")
