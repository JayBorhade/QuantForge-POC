"""Portfolio model."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.trade import Trade
    from app.models.user import User


class PortfolioStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    risk_exposure: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    status: Mapped[PortfolioStatus] = mapped_column(
        Enum(PortfolioStatus), default=PortfolioStatus.ACTIVE
    )
    broker: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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

    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    orders: Mapped[List["Order"]] = relationship("Order", cascade="all, delete-orphan")

    trades: Mapped[List["Trade"]] = relationship(
        "Trade", back_populates="portfolio", cascade="all, delete-orphan"
    )
