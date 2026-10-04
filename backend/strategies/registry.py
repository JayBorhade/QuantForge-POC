"""Strategy registry mapping types to implementations."""

from typing import Dict, Type

from strategies.ai_sentiment import AISentimentStrategy
from strategies.base import BaseStrategy
from strategies.breakout import BreakoutStrategy
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.vwap_intraday import VWAPIntradayStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "ema_crossover": EMACrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "vwap_intraday": VWAPIntradayStrategy,
    "breakout": BreakoutStrategy,
    "ai_sentiment": AISentimentStrategy,
}


def get_strategy(strategy_type: str, symbol: str, parameters: dict, mode: str = "paper") -> BaseStrategy:
    cls = STRATEGY_REGISTRY.get(strategy_type)
    if not cls:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    return cls(symbol=symbol, parameters=parameters, mode=mode)
