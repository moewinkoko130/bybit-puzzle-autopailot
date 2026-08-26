import os
from dataclasses import dataclass
from typing import Callable

from app.risk import get_risk_percent
from app.exchange.client import BybitV5Client, ExchangeAPIError, ExchangeSafetyError


LIVE_PHRASE = "ENABLE LIVE TRADING"


class LivePreflightError(ExchangeSafetyError):
    pass


@dataclass(frozen=True)
class LivePreflight:
    symbol: str
    risk_percent: float
    account_balance: float
    confirmed: bool


def confirm_live_trading(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    output_fn("LIVE TRADING WARNING: real funds may be at risk.")
    output_fn(f'Type exactly "{LIVE_PHRASE}" to continue.')
    if input_fn("Confirmation: ") != LIVE_PHRASE:
        return False
    return input_fn("Final confirmation (type YES): ").strip().upper() == "YES"


def _valid_risk_limits() -> bool:
    try:
        raw_risk = os.getenv("MAX_RISK_PERCENT", "1.0").strip()
        risk = float(raw_risk)
        daily = float(os.getenv("DAILY_LOSS_LIMIT", "5.0"))
        losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
        cooldown = int(os.getenv("POST_TRADE_COOLDOWN_SECONDS", "0"))
    except (TypeError, ValueError):
        return False
    return 0 < risk <= 5 and 0 < daily <= 100 and losses > 0 and cooldown >= 0


def run_live_preflight(
    client: BybitV5Client,
    symbol: str,
    api_key: str,
    api_secret: str,
    confirmed: bool,
) -> LivePreflight:
    if not confirmed:
        raise LivePreflightError("Live confirmation was not completed.")
    if not api_key.strip() or not api_secret.strip():
        raise LivePreflightError("Live API credentials are required.")
    if os.getenv("BYBIT_TESTNET", "true").lower() != "false":
        raise LivePreflightError("BYBIT_TESTNET=false is required for live mode.")
    if client.testnet or client.endpoint != BybitV5Client.MAINNET_ENDPOINT:
        raise LivePreflightError("Live client endpoint/environment mismatch.")
    if not _valid_risk_limits():
        raise LivePreflightError("Live risk limits are invalid or exceed the 5% cap.")
    if not symbol.strip() or any(character.isspace() for character in symbol):
        raise LivePreflightError("Live symbol is invalid.")
    try:
        rules = client.get_instrument_rules(symbol.upper())
        if rules.tick_size <= 0 or rules.qty_step <= 0 or rules.min_qty <= 0:
            raise LivePreflightError("Live symbol precision rules are invalid.")
        response = client.get_wallet_balance()
        account = response.get("result", {}).get("list", [])
        if not account:
            raise LivePreflightError("Live account query returned no account.")
        balance = float(account[0].get("totalEquity", account[0].get("totalWalletBalance", 0)))
        if balance <= 0:
            raise LivePreflightError("Live account balance is invalid.")
    except LivePreflightError:
        raise
    except (ExchangeAPIError, KeyError, TypeError, ValueError) as exc:
        raise LivePreflightError(f"Live preflight failed: {exc}") from exc
    return LivePreflight(symbol=symbol.upper(), risk_percent=get_risk_percent(), account_balance=balance, confirmed=True)
