"""Strategy and strategy run models."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trade import Trade
    from app.models.user import User


class StrategyType(str, enum.Enum):
    EMA_CROSSOVER = "ema_crossover"
    RSI_MEAN_REVERSION = "rsi_mean_reversion"
    VWAP_INTRADAY = "vwap_intraday"
    BREAKOUT = "breakout"
    AI_SENTIMENT = "ai_sentiment"
    CUSTOM = "custom"


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunMode(str, enum.Enum):
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus), default=StrategyStatus.DRAFT
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="strategies")
    runs: Mapped[List["StrategyRun"]] = relationship(
        "StrategyRun", back_populates="strategy", cascade="all, delete-orphan"
    )
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="strategy")


class StrategyRun(Base):
    __tablename__ = "strategy_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[RunMode] = mapped_column(Enum(RunMode), default=RunMode.PAPER)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.PENDING)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    total_trades: Mapped[int] = mapped_column(default=0)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    configuration_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    data_revision: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    initial_capital: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    input_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    worker_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    worker_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="runs")
