"""Normalized market-data event contracts."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: Decimal | None
    ask: Decimal | None
    last_price: Decimal
    event_time: datetime
    source: str
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("Quote symbol must be normalized uppercase")
        if self.last_price <= 0:
            raise ValueError("Quote last_price must be positive")
        if self.bid is not None and self.bid <= 0:
            raise ValueError("Quote bid must be positive")
        if self.ask is not None and self.ask <= 0:
            raise ValueError("Quote ask must be positive")
        if self.event_time.tzinfo is None:
            raise ValueError("Quote event_time must be timezone-aware")

    def as_dict(self) -> dict:
        return {
            "type": "quote",
            "symbol": self.symbol,
            "bid": str(self.bid) if self.bid is not None else None,
            "ask": str(self.ask) if self.ask is not None else None,
            "last_price": str(self.last_price),
            "event_time": self.event_time.astimezone(timezone.utc).isoformat(),
            "source": self.source,
            "sequence": self.sequence,
        }
