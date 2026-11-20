"""Unavailable placeholder for a future provider-backed sentiment strategy.

This strategy intentionally refuses to fabricate sentiment from hard-coded
headlines or pseudo-random values. It can be enabled only after real, licensed
news/social providers, timestamps, missing-data handling, and validation are
implemented.
"""

from typing import Any, Dict

import pandas as pd

from strategies.base import BaseStrategy


class AISentimentStrategy(BaseStrategy):
    """Reserved strategy identifier; no sentiment provider is currently wired."""

    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "news_weight": 0.4,
            "reddit_weight": 0.3,
            "social_weight": 0.3,
            "buy_threshold": 0.6,
            "sell_threshold": -0.6,
            "min_confidence": 0.55,
            "position_size_pct": 0.05,
        }

    def calculate_sentiment(self) -> Dict[str, Any]:
        raise RuntimeError(
            "AI sentiment is unavailable: no real news or social sentiment "
            "provider is configured. No synthetic sentiment will be generated."
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # Fail closed. Returning HOLDs would falsely imply a real sentiment
        # evaluation took place, so callers receive an explicit unavailable error.
        self.calculate_sentiment()
        return df.copy()
