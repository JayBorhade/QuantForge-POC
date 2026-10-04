"""Base strategy class."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class Signal(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    signal: Signal
    price: float
    quantity: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    equity_curve: List[Dict[str, Any]]
    trade_history: List[Dict[str, Any]]


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, symbol: str, parameters: Dict[str, Any], mode: str = "paper"):
        self.symbol = symbol
        self.parameters = parameters
        self.mode = mode
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from OHLCV data."""
        pass

    @abstractmethod
    def get_default_parameters(self) -> Dict[str, Any]:
        """Return default strategy parameters."""
        pass

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        risk_pct: float = 0.02,
    ) -> float:
        risk_amount = capital * risk_pct
        return max(risk_amount / price, 0.0)

    def log_signal(self, signal: TradeSignal) -> None:
        self.logger.info(
            "%s signal on %s @ %.4f | SL: %s | TP: %s",
            signal.signal.value,
            self.symbol,
            signal.price,
            signal.stop_loss,
            signal.take_profit,
        )
