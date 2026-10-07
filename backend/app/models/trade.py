"""Trade model."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.strategy import Strategy


class TradeSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TradeMode(str, enum.Enum):
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus), default=TradeStatus.PENDING
    )
    mode: Mapped[TradeMode] = mapped_column(Enum(TradeMode), default=TradeMode.PAPER)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entry_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="trades")
    strategy: Mapped[Optional["Strategy"]] = relationship("Strategy", back_populates="trades")
