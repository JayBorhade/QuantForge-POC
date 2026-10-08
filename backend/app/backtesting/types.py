"""Typed domain objects for deterministic backtesting."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: Decimal = Decimal("100000")
    position_size_pct: Decimal = Decimal("0.10")
    transaction_cost_pct: Decimal = Decimal("0.001")
    slippage_pct: Decimal = Decimal("0.0005")
    risk_free_rate: Decimal = Decimal("0.02")
    def validate(self) -> None:
        if self.initial_capital <= 0: raise ValueError("initial_capital must be positive")
        if not Decimal("0") < self.position_size_pct <= Decimal("1"): raise ValueError("position_size_pct must be in (0, 1]")
        if not Decimal("0") <= self.transaction_cost_pct < Decimal("1"): raise ValueError("transaction_cost_pct must be in [0, 1)")
        if not Decimal("0") <= self.slippage_pct < Decimal("1"): raise ValueError("slippage_pct must be in [0, 1)")
        if self.risk_free_rate < 0: raise ValueError("risk_free_rate must be non-negative")

@dataclass(frozen=True)
class BacktestBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    def validate(self) -> None:
        if min(self.open, self.high, self.low, self.close) <= 0: raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close): raise ValueError("invalid OHLC relationship")

@dataclass(frozen=True)
class BacktestTrade:
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    return_pct: Decimal
    reason: str

@dataclass(frozen=True)
class BacktestResult:
    initial_capital: Decimal
    final_capital: Decimal
    total_return_pct: Decimal
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal
    total_trades: int
    equity_curve: Sequence[Mapping[str, Any]]
    trades: Sequence[BacktestTrade]
