"""Immutable specification for a reproducible backtest run."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.backtesting.fingerprint import configuration_fingerprint

@dataclass(frozen=True)
class BacktestRunSpec:
    strategy_type: str
    symbol: str
    parameters: dict
    initial_capital: Decimal
    position_size_pct: Decimal
    transaction_cost_pct: Decimal
    slippage_pct: Decimal
    start_date: datetime
    end_date: datetime
    data_source: str
    data_revision: str

    def fingerprint(self) -> str:
        config={"initial_capital":self.initial_capital,"position_size_pct":self.position_size_pct,"transaction_cost_pct":self.transaction_cost_pct,"slippage_pct":self.slippage_pct}
        return configuration_fingerprint(strategy_type=self.strategy_type,symbol=self.symbol,parameters=self.parameters,config=config,start_date=self.start_date.isoformat(),end_date=self.end_date.isoformat())
