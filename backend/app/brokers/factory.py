"""Canonical broker adapter factory."""

from __future__ import annotations

from typing import Protocol

from app.brokers.angel_one import AngelOneBrokerAdapter
from app.brokers.binance import BinanceBrokerAdapter
from app.brokers.base import BrokerAdapter
from app.brokers.zerodha import ZerodhaBrokerAdapter


class BrokerConnectionAdapter(BrokerAdapter, Protocol):
    async def connect(self) -> bool: ...
    async def get_quote(self, symbol: str, **kwargs): ...
    async def get_positions(self) -> list[dict]: ...


def get_broker_adapter(
    broker: str,
    api_key: str,
    api_secret: str,
    access_token: str | None = None,
) -> BrokerConnectionAdapter:
    adapters = {
        "zerodha": ZerodhaBrokerAdapter,
        "binance": BinanceBrokerAdapter,
        "angel_one": AngelOneBrokerAdapter,
    }
    cls = adapters.get(broker.lower())
    if cls is None:
        raise ValueError(f"Unsupported broker: {broker}")
    return cls(api_key=api_key, api_secret=api_secret, access_token=access_token)
