from datetime import datetime, timedelta

import pytest

from app.risk import RiskGatekeeper, calculate_risk


def test_long_risk_math():
    result = calculate_risk(100, 1000, 1, 2, "BUY")
    assert result.stop_loss == pytest.approx(99)
    assert result.take_profit == pytest.approx(102)
    assert result.position_size == pytest.approx(10)


def test_short_risk_math():
    result = calculate_risk(100, 1000, 1, 2, "SELL")
    assert result.stop_loss == pytest.approx(101)
    assert result.take_profit == pytest.approx(98)
    assert result.position_size == pytest.approx(10)


@pytest.mark.parametrize(
    ("daily_pnl", "consecutive_losses", "expected"),
    [(-50, 0, "Daily loss"), (0, 3, "consecutive")],
)
def test_gatekeeper_rejects_limits(monkeypatch, daily_pnl, consecutive_losses, expected):
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "5")
    monkeypatch.setenv("MAX_CONSECUTIVE_LOSSES", "3")
    decision = RiskGatekeeper().validate(1000, daily_pnl, consecutive_losses)
    assert not decision.approved
    assert expected.lower() in decision.reason.lower()


def test_gatekeeper_rejects_during_cooldown(monkeypatch):
    now = datetime.now()
    monkeypatch.setenv("POST_TRADE_COOLDOWN_SECONDS", "60")
    decision = RiskGatekeeper(clock=lambda: now).validate(
        1000, last_trade_at=now - timedelta(seconds=1)
    )
    assert not decision.approved
    assert "cooldown" in decision.reason.lower()
