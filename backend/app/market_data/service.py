"""Connection-scoped market-data subscription service."""
import asyncio
from collections.abc import AsyncIterator

from app.market_data.binance_stream import BinanceQuoteStream
from app.market_data.types import Quote


class MarketDataService:
    """Provides bounded, provider-normalized quote streams to API consumers."""

    MAX_SYMBOLS_PER_CONNECTION = 5

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.replace("/", "").strip().upper()
        if not normalized.isalnum() or not 5 <= len(normalized) <= 20:
            raise ValueError("Invalid market-data symbol")
        return normalized

    async def stream(self, symbol: str) -> AsyncIterator[Quote]:
        normalized = self.normalize_symbol(symbol)
        stream = BinanceQuoteStream(normalized)
        async for quote in stream.events():
            yield quote

    async def multiplex(self, symbols: list[str]) -> AsyncIterator[Quote]:
        normalized = list(dict.fromkeys(self.normalize_symbol(s) for s in symbols))
        if not normalized or len(normalized) > self.MAX_SYMBOLS_PER_CONNECTION:
            raise ValueError(
                f"Subscribe to 1-{self.MAX_SYMBOLS_PER_CONNECTION} symbols per connection"
            )

        queue: asyncio.Queue[Quote] = asyncio.Queue(maxsize=256)
        tasks = []

        async def consume(symbol: str):
            async for quote in self.stream(symbol):
                if queue.full():
                    queue.get_nowait()
                await queue.put(quote)

        try:
            tasks = [asyncio.create_task(consume(symbol)) for symbol in normalized]
            while True:
                yield await queue.get()
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
