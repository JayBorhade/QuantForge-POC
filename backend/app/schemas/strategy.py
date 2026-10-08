"""Strategy schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.strategy import RunMode, StrategyStatus, StrategyType
from app.services.strategy_scheduler import validate_cron_expression


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    strategy_type: StrategyType
    symbol: str = Field(..., min_length=1, max_length=32)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_paper: bool = True
    schedule_cron: Optional[str] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[StrategyStatus] = None
    is_paper: Optional[bool] = None
    schedule_cron: Optional[str] = None


class StrategyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    strategy_type: StrategyType
    symbol: str
    status: StrategyStatus
    parameters: Dict[str, Any]
    is_paper: bool
    schedule_cron: Optional[str]
    schedule_portfolio_id: Optional[UUID]
    last_scheduled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BacktestRequest(BaseModel):
    strategy_id: UUID
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=100000.0, gt=0, allow_inf_nan=False)
    mode: RunMode = RunMode.BACKTEST

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be earlier than end_date")
        if self.mode != RunMode.BACKTEST:
            raise ValueError("Only BACKTEST mode is supported by this endpoint")
        return self


class BacktestResponse(BaseModel):
    run_id: UUID
    status: str
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    total_return: Optional[float]
    win_rate: Optional[float]
    total_trades: int
    equity_curve: Optional[list]
    trade_history: Optional[list]

    model_config = {"from_attributes": True}
