from app.strategy import SignalEvent, analyze_prices, ema_signal


def crossing_prices():
    return [100.0] * 21 + [110.0]


def test_ema_signal_requires_a_real_upward_crossing():
    assert ema_signal(crossing_prices()) == "BUY"
    assert ema_signal(crossing_prices() + [110.0]) == "HOLD"


def test_ema_signal_requires_a_real_downward_crossing():
    prices = [110.0] * 21 + [100.0]
    assert ema_signal(prices) == "SELL"
    assert ema_signal(prices + [100.0]) == "HOLD"


def test_analysis_exposes_typed_signal_event():
    result = analyze_prices(crossing_prices())
    assert isinstance(result["event"], SignalEvent)
    assert result["event"].action == "BUY"
