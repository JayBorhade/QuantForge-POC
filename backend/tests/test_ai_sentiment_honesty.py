"""AI sentiment placeholder must never synthesize market sentiment."""

import unittest
import pandas as pd

from strategies.ai_sentiment import AISentimentStrategy


class AISentimentHonestyTests(unittest.TestCase):
    def test_sentiment_calculation_fails_closed_without_provider(self):
        strategy = AISentimentStrategy("AAPL", {})
        with self.assertRaisesRegex(RuntimeError, "no real news or social sentiment provider"):
            strategy.calculate_sentiment()

    def test_signal_generation_does_not_emit_synthetic_signals(self):
        strategy = AISentimentStrategy("AAPL", {})
        frame = pd.DataFrame({"close": [100.0, 101.0]})
        with self.assertRaises(RuntimeError):
            strategy.generate_signals(frame)


if __name__ == "__main__":
    unittest.main()
