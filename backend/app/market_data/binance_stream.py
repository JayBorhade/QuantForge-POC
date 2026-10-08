"""Resilient public Binance quote stream."""
import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal

import websockets

from app.market_data.types import Quote

logger = logging.getLogger(__name__)


class BinanceQuoteStream:
    BASE_URL = "wss://stream.binance.com:9443/ws"

    def __init__(self, symbol: str, *, reconnect_delay: float = 1.0, max_reconnect_delay: float = 30.0):
        normalized = symbol.replace("/", "").strip().lower()
        if not normalized.isalnum() or len(normalized) < 5 or len(normalized) > 20:
            raise ValueError("Invalid Binance symbol")
        self.symbol = normalized
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

    @staticmethod
    def parse_message(message: str) -> Quote:
        payload = json.loads(message)
        if payload.get("e") != "bookTicker":
            raise ValueError("Unsupported Binance market-data event")
        symbol = str(payload["s"]).upper()
        bid = Decimal(str(payload["b"]))
        ask = Decimal(str(payload["a"]))
        last_price = (bid + ask) / Decimal("2")
        event_ms = int(payload["E"])
        return Quote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last_price=last_price,
            event_time=datetime.fromtimestamp(event_ms / 1000, tz=timezone.utc),
            source="binance.websocket",
            sequence=int(payload["u"]) if payload.get("u") is not None else None,
        )

    async def events(self) -> AsyncIterator[Quote]:
        delay = self.reconnect_delay
        while True:
            try:
                async with websockets.connect(
                    f"{self.BASE_URL}/{self.symbol}@bookTicker",
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_queue=128,
                ) as socket:
                    delay = self.reconnect_delay
                    async for message in socket:
                        try:
                            yield self.parse_message(message)
                        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                            logger.warning("Dropped malformed Binance market-data event")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Binance quote stream disconnected for %s", self.symbol)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.max_reconnect_delay)
