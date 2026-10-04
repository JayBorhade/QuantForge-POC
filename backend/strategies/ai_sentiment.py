"""AI Sentiment Strategy — news and social sentiment scoring."""

from typing import Any, Dict, List

import pandas as pd

from strategies.base import BaseStrategy, Signal


class AISentimentStrategy(BaseStrategy):
    """
    Combines news, Reddit, and social sentiment.
    Generates confidence score and buy/sell bias.
    """

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

    def _score_news(self, symbol: str) -> float:
        """Score news sentiment (-1 to 1). Production: integrate news API."""
        headlines = [
            f"{symbol} beats earnings expectations",
            f"Analysts upgrade {symbol} rating",
            f"Market volatility affects {symbol}",
        ]
        positive_words = {"beats", "upgrade", "growth", "bullish", "surge", "record"}
        negative_words = {"miss", "downgrade", "decline", "bearish", "crash", "lawsuit"}
        score = 0.0
        for headline in headlines:
            words = headline.lower().split()
            score += sum(1 for w in words if w in positive_words)
            score -= sum(1 for w in words if w in negative_words)
        return max(min(score / len(headlines), 1.0), -1.0)

    def _score_reddit(self, symbol: str) -> float:
        """Reddit sentiment proxy. Production: PRAW/API integration."""
        import random
        random.seed(hash(symbol) % 10000)
        return random.uniform(-0.5, 0.8)

    def _score_social(self, symbol: str) -> float:
        """Social media sentiment proxy."""
        import random
        random.seed(hash(symbol + "social") % 10000)
        return random.uniform(-0.4, 0.7)

    def calculate_sentiment(self) -> Dict[str, Any]:
        params = {**self.get_default_parameters(), **self.parameters}
        news = self._score_news(self.symbol) * params["news_weight"]
        reddit = self._score_reddit(self.symbol) * params["reddit_weight"]
        social = self._score_social(self.symbol) * params["social_weight"]
        composite = news + reddit + social
        confidence = min(abs(composite) + 0.3, 1.0)

        if composite >= params["buy_threshold"]:
            bias = Signal.BUY
        elif composite <= params["sell_threshold"]:
            bias = Signal.SELL
        else:
            bias = Signal.HOLD

        return {
            "composite_score": round(composite, 4),
            "confidence": round(confidence, 4),
            "bias": bias.value,
            "components": {
                "news": round(news / params["news_weight"], 4),
                "reddit": round(reddit / params["reddit_weight"], 4),
                "social": round(social / params["social_weight"], 4),
            },
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        params = {**self.get_default_parameters(), **self.parameters}
        sentiment = self.calculate_sentiment()
        df = df.copy()
        df["signal"] = Signal.HOLD.value
        df["sentiment_score"] = sentiment["composite_score"]
        df["confidence"] = sentiment["confidence"]

        if sentiment["confidence"] >= params["min_confidence"]:
            if sentiment["bias"] == Signal.BUY.value:
                df.iloc[-1, df.columns.get_loc("signal")] = Signal.BUY.value
            elif sentiment["bias"] == Signal.SELL.value:
                df.iloc[-1, df.columns.get_loc("signal")] = Signal.SELL.value

        return df
