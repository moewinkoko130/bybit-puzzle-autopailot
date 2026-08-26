import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Candle:
    """One OHLCV candle with a timezone-aware UTC timestamp."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("Candle high/low does not contain open/close.")


class HistoricalDataLoader:
    """Load candles from CSV, JSON, or an API callback and filter date ranges."""

    @staticmethod
    def _timestamp(value: Any) -> datetime:
        if isinstance(value, (int, float)):
            if value > 10_000_000_000:
                value /= 1000
            return datetime.fromtimestamp(value, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @classmethod
    def _candle(cls, row: dict[str, Any] | list[Any]) -> Candle:
        if isinstance(row, list):
            values = row
            return Candle(cls._timestamp(values[0]), *(float(value) for value in values[1:6]))
        timestamp = row.get("timestamp", row.get("time", row.get("startTime")))
        return Candle(
            cls._timestamp(timestamp),
            float(row["open"]), float(row["high"]), float(row["low"]),
            float(row["close"]), float(row.get("volume", 0.0)),
        )

    @classmethod
    def load(
        cls,
        source: str | Path | Iterable[dict[str, Any] | list[Any]],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Load and chronologically sort candles, optionally applying inclusive dates."""
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.suffix.lower() == ".csv":
                with path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
            elif path.suffix.lower() == ".json":
                with path.open(encoding="utf-8") as handle:
                    rows = json.load(handle)
            else:
                raise ValueError("Historical data must be CSV or JSON.")
        else:
            rows = list(source)
        candles = sorted((cls._candle(row) for row in rows), key=lambda item: item.timestamp)
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return [candle for candle in candles if (start is None or candle.timestamp >= start) and (end is None or candle.timestamp <= end)]

    @classmethod
    def from_api(
        cls,
        fetch: Callable[..., list[dict[str, Any]] | list[list[Any]]],
        symbol: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Adapt an API fetch callback returning Bybit-style kline rows."""
        rows = fetch(symbol=symbol, interval=interval, start=start, end=end)
        return cls.load(rows, start=start, end=end)
