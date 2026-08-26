from datetime import datetime, timezone
import warnings

import pytest

from app.paper import (
    CLOSED,
    MANUAL_CLOSE,
    OPEN,
    STOP_LOSS,
    TAKE_PROFIT,
    PaperExecutor,
    close_paper_position,
    open_paper_position,
)


class FixedClock:
    def __init__(self):
        self.value = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self):
        self.value = self.value.replace(second=self.value.second + 1)


def executor(tmp_path):
    return PaperExecutor(str(tmp_path / "paper.sqlite3"), clock=FixedClock())


def test_buy_position_creation(tmp_path):
    position = executor(tmp_path).open_position(
        "BUY", 100, 2, 90, 120, "BTCUSDT", "5", "EMA"
    )
    assert position.trade_id
    assert position.symbol == "BTCUSDT"
    assert position.timeframe == "5"
    assert position.strategy == "EMA"
    assert position.status == OPEN


def test_sell_position_creation(tmp_path):
    position = executor(tmp_path).open_position("SELL", 100, 2, 110, 80)
    assert position.side == "SELL"
    assert position.entry_price == 100
    assert position.quantity == 2


def test_buy_pnl(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("BUY", 100, 2, 90, 120)
    assert engine.close_position(110).pnl == 20


def test_sell_pnl(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("SELL", 100, 2, 110, 80)
    assert engine.close_position(90).pnl == 20


def test_stop_loss_and_take_profit(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("BUY", 100, 1, 90, 120)
    assert engine.check_exit(90) == STOP_LOSS
    engine.close_position(90, STOP_LOSS)
    engine.open_position("BUY", 100, 1, 90, 120)
    assert engine.close_at_trigger(120).exit_reason == TAKE_PROFIT


def test_manual_close(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("BUY", 100, 1, 90, 120)
    assert engine.close_position(105, MANUAL_CLOSE).exit_reason == MANUAL_CLOSE


@pytest.mark.parametrize("signal", ["HOLD", "", "BUYSELL"])
def test_invalid_signal(tmp_path, signal):
    with pytest.raises(ValueError, match="BUY or SELL"):
        executor(tmp_path).open_position(signal, 100, 1, 90, 120)


def test_invalid_quantity(tmp_path):
    with pytest.raises(ValueError, match="Quantity"):
        executor(tmp_path).open_position("BUY", 100, 0, 90, 120)


@pytest.mark.parametrize("prices", [(0, 90, 120), (100, 0, 120), (100, 90, 0)])
def test_invalid_prices(tmp_path, prices):
    with pytest.raises(ValueError, match="price|Price|loss|profit"):
        executor(tmp_path).open_position("BUY", prices[0], 1, prices[1], prices[2])


def test_duplicate_or_conflicting_position_is_rejected(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("BUY", 100, 1, 90, 120)
    with pytest.raises(ValueError, match="already exists"):
        engine.open_position("SELL", 100, 1, 110, 80)


def test_closed_history_survives_restart(tmp_path):
    database = tmp_path / "paper.sqlite3"
    first = PaperExecutor(str(database))
    position = first.open_position("BUY", 100, 1, 90, 120, "BTCUSDT", "5", "EMA")
    first.close_position(120, TAKE_PROFIT)
    first.close()

    second = PaperExecutor(str(database))
    assert second.position is None
    trade = second.closed_trades()[0]
    assert trade.trade_id == position.trade_id
    assert trade.status == CLOSED
    second.close()


def test_executor_context_manager_closes_connection(tmp_path):
    database = tmp_path / "paper.sqlite3"
    with PaperExecutor(str(database)) as engine:
        engine.open_position("BUY", 100, 2, 90, 120)

    with pytest.raises(Exception):
        engine.closed_trades()


def test_database_parent_directory_is_created(tmp_path):
    database = tmp_path / "nested" / "paper.sqlite3"
    engine = PaperExecutor(database)
    assert database.exists()
    engine.close()


def test_open_position_survives_restart(tmp_path):
    database = tmp_path / "paper.sqlite3"
    first = PaperExecutor(database)
    position = first.open_position("SELL", 100, 2, 110, 80)
    first.close()

    second = PaperExecutor(database)
    assert second.position.trade_id == position.trade_id
    assert second.position.side == "SELL"
    second.close()


def test_close_is_idempotent(tmp_path):
    engine = executor(tmp_path)
    engine.close()
    engine.close()


def test_legacy_helpers_are_deprecated():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        position = open_paper_position("BUY", 100, 1, 90, 120)
        close_paper_position(position, 110, MANUAL_CLOSE)

    assert len([warning for warning in caught if issubclass(
        warning.category, DeprecationWarning
    )]) == 2


def test_trade_persists_gross_and_net_pnl(tmp_path):
    engine = executor(tmp_path)
    engine.open_position("BUY", 100, 2, 90, 120)
    trade = engine.close_position(110, fees=1.5, slippage=0.5)

    assert trade.gross_pnl == 20
    assert trade.net_pnl == 17.5
    assert trade.realized_pnl == 17.5

    columns = {
        row["name"]
        for row in engine._connection.execute(
            "PRAGMA table_info(paper_trades)"
        ).fetchall()
    }
    assert {"gross_pnl", "fees", "net_pnl", "status"} <= columns
