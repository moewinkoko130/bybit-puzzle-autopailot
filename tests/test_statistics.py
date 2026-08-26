from app.paper import PaperTrade, calculate_statistics


def trade(pnl):
    return PaperTrade("BUY", 100, 100, 1, pnl, "MANUAL_CLOSE", "", "")


def test_statistics_include_profit_factor_and_max_drawdown():
    stats = calculate_statistics([trade(10), trade(-4), trade(-3), trade(8)])
    assert stats["total_pnl"] == 11
    assert stats["average_pnl"] == 2.75
    assert stats["profit_factor"] == 18 / 7
    assert stats["max_drawdown"] == 7
