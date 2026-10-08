"""Deterministic market-data contract tests."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.binance_stream import BinanceQuoteStream
from app.market_data.service import MarketDataService
from app.market_data.types import Quote


class MarketDataTests(unittest.TestCase):
    def test_binance_book_ticker_normalizes_quote(self):
        quote = BinanceQuoteStream.parse_message(
            '{"e":"bookTicker","E":1791432000123,"s":"BTCUSDT","b":"100.00","a":"102.00","u":42}'
        )
        self.assertEqual(quote.symbol, "BTCUSDT")
        self.assertEqual(quote.last_price, Decimal("101"))
        self.assertEqual(quote.sequence, 42)
        self.assertEqual(quote.source, "binance.websocket")

    def test_rejects_non_market_event(self):
        with self.assertRaises(ValueError):
            BinanceQuoteStream.parse_message('{"e":"trade","s":"BTCUSDT"}')

    def test_normalizes_symbols(self):
        self.assertEqual(MarketDataService.normalize_symbol("btc/usdt"), "BTCUSDT")

    def test_limits_subscription_fanout(self):
        self.assertEqual(MarketDataService.MAX_SYMBOLS_PER_CONNECTION, 5)
        with self.assertRaises(ValueError):
            MarketDataService().normalize_symbol("BTC")

    def test_quote_requires_aware_timestamp(self):
        with self.assertRaises(ValueError):
            Quote(
                symbol="BTCUSDT",
                bid=Decimal("100"),
                ask=Decimal("101"),
                last_price=Decimal("100.5"),
                event_time=datetime.now(),
                source="test",
            )


if __name__ == "__main__":
    unittest.main()
