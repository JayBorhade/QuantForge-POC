"""Historical bar contract for the backtesting engine."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from app.backtesting.types import BacktestBar

class HistoricalDataError(ValueError):
    """Raised when historical data violates the deterministic contract."""

@dataclass(frozen=True)
class HistoricalBarSet:
    symbol: str
    bars: tuple[BacktestBar, ...]
    source: str
    revision: str = "unknown"

    def validate(self) -> None:
        if not self.symbol.strip(): raise HistoricalDataError("symbol is required")
        if not self.bars: raise HistoricalDataError("historical dataset is empty")
        previous=None
        for bar in self.bars:
            bar.validate()
            if previous is not None and bar.timestamp <= previous:
                raise HistoricalDataError("historical bars must be strictly chronological")
            previous=bar.timestamp

class HistoricalDataProvider:
    def load(self, symbol: str, start: datetime, end: datetime) -> HistoricalBarSet:
        raise NotImplementedError

def validate_historical_bars(bars: Iterable[BacktestBar], symbol: str, source: str, revision: str="unknown") -> HistoricalBarSet:
    dataset=HistoricalBarSet(symbol=symbol.upper(),bars=tuple(bars),source=source,revision=revision)
    dataset.validate()
    return dataset
