"""Strategy registry and strict parameter validation."""

import math
import re
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

_BACKTEST_ONLY_PARAMETERS = {"transaction_cost_pct", "slippage_pct", "benchmark_symbol"}
_INTEGER_PARAMETERS = {
    "rsi_period", "fast_ema", "slow_ema", "lookback", "atr_period",
    "confirmation_bars", "cooldown_bars",
}
_UNIT_INTERVAL_PARAMETERS = {
    "position_size_pct", "risk_pct", "stop_loss_pct", "take_profit_pct",
    "trailing_stop_pct", "transaction_cost_pct", "slippage_pct",
    "volatility_threshold",
}
_POSITIVE_PARAMETERS = {"atr_multiplier", "volume_multiplier"}


def validate_strategy_parameters(strategy_type: str, parameters: dict | None) -> dict:
    """Reject unknown or out-of-range strategy parameters before persistence."""
    if strategy_type not in STRATEGY_REGISTRY:
        raise ValueError("Unsupported strategy type")
    if parameters is None:
        return {}
    if not isinstance(parameters, dict):
        raise ValueError("Strategy parameters must be an object")

    defaults = STRATEGY_REGISTRY[strategy_type]("", {}).get_default_parameters()
    allowed = set(defaults) | _BACKTEST_ONLY_PARAMETERS
    unknown = set(parameters) - allowed
    if unknown:
        raise ValueError(f"Unsupported parameter(s): {', '.join(sorted(unknown))}")

    validated = dict(parameters)
    for name, value in validated.items():
        if name in {"session_start", "session_end"}:
            if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\\d|2[0-3]):[0-5]\\d", value):
                raise ValueError(f"{name} must use HH:MM in 24-hour time")
            continue
        if name == "benchmark_symbol":
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9.^=_-]{1,24}", value):
                raise ValueError("benchmark_symbol contains invalid characters")
            continue
        default = defaults.get(name)
        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")
            continue
        if isinstance(default, (int, float)) or name in _BACKTEST_ONLY_PARAMETERS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                if name in _BACKTEST_ONLY_PARAMETERS and name != "benchmark_symbol":
                    raise ValueError(f"{name} must be numeric")
                raise ValueError(f"{name} must be numeric")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if name in _INTEGER_PARAMETERS:
            if int(value) != value or not 1 <= int(value) <= 1000:
                raise ValueError(f"{name} must be an integer between 1 and 1000")
        if name in _UNIT_INTERVAL_PARAMETERS and not 0 <= float(value) <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
        if name in _POSITIVE_PARAMETERS and float(value) <= 0:
            raise ValueError(f"{name} must be positive")

    merged = {**defaults, **validated}
    if "fast_ema" in merged and "slow_ema" in merged and merged["fast_ema"] >= merged["slow_ema"]:
        raise ValueError("fast_ema must be less than slow_ema")
    if "oversold" in merged and "overbought" in merged:
        if not (0 <= float(merged["oversold"]) < float(merged["overbought"]) <= 100):
            raise ValueError("oversold must be below overbought and both must be between 0 and 100")
    return validated


def get_strategy(strategy_type: str, symbol: str, parameters: dict, mode: str = "paper") -> BaseStrategy:
    cls = STRATEGY_REGISTRY.get(strategy_type)
    if not cls:
        raise ValueError("Unsupported strategy type")
    validated = validate_strategy_parameters(strategy_type, parameters)
    return cls(symbol=symbol, parameters=validated, mode=mode)
