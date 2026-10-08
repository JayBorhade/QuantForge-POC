"""Historical portfolio equity snapshot."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        Index("ix_portfolio_snapshots_portfolio_recorded_at", "portfolio_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    position_market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    daily_return: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=0)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=0)
