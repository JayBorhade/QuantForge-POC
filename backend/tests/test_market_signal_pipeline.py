"""Deterministic tests for the market-data signal pipeline."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.signal_pipeline import MarketSignalPipeline, SignalAction
from app.market_data.types import Quote


def quote(sequence: int, price: str = "100") -> Quote:
    return Quote(
        symbol="BTCUSDT",
        bid=Decimal(price) - Decimal("1"),
        ask=Decimal(price) + Decimal("1"),
        last_price=Decimal(price),
        event_time=datetime(2026, 10, 8, 10, 0, sequence, tzinfo=timezone.utc),
        source="test",
        sequence=sequence,
    )


class SignalPipelineTests(unittest.TestCase):
    def test_emits_normalized_signal(self):
        event = MarketSignalPipeline().evaluate(
            strategy_id="strategy-1",
            quote=quote(1),
            evaluator=lambda _: SignalAction.BUY,
        )
        self.assertEqual(event.action, SignalAction.BUY)
        self.assertEqual(event.price, "100")

    def test_deduplicates_out_of_order_sequences(self):
        pipeline = MarketSignalPipeline()
        self.assertIsNotNone(
            pipeline.evaluate(strategy_id="s", quote=quote(5), evaluator=lambda _: "hold")
        )
        self.assertIsNone(
            pipeline.evaluate(strategy_id="s", quote=quote(5), evaluator=lambda _: "buy")
        )
        self.assertIsNone(
            pipeline.evaluate(strategy_id="s", quote=quote(4), evaluator=lambda _: "buy")
        )

    def test_allows_independent_strategies(self):
        pipeline = MarketSignalPipeline()
        first = pipeline.evaluate(strategy_id="s1", quote=quote(1), evaluator=lambda _: "buy")
        second = pipeline.evaluate(strategy_id="s2", quote=quote(1), evaluator=lambda _: "sell")
        self.assertEqual(first.action, SignalAction.BUY)
        self.assertEqual(second.action, SignalAction.SELL)

    def test_rejects_invalid_signal(self):
        with self.assertRaises(ValueError):
            MarketSignalPipeline().evaluate(
                strategy_id="s", quote=quote(1), evaluator=lambda _: "explode"
            )


if __name__ == "__main__":
    unittest.main()
