"""Broker adapter factory."""

from typing import Optional

from brokers.angel_one import AngelOneAdapter
from brokers.base import BaseBrokerAdapter
from brokers.binance import BinanceAdapter
from brokers.zerodha import ZerodhaAdapter


def get_broker_adapter(
    broker: str,
    api_key: str,
    api_secret: str,
    access_token: Optional[str] = None,
) -> BaseBrokerAdapter:
    adapters = {
        "zerodha": ZerodhaAdapter,
        "binance": BinanceAdapter,
        "angel_one": AngelOneAdapter,
    }
    cls = adapters.get(broker.lower())
    if not cls:
        raise ValueError(f"Unsupported broker: {broker}")
    return cls(api_key=api_key, api_secret=api_secret, access_token=access_token)
