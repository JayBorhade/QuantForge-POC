"""Portfolio pre-trade risk limits and kill-switch state."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RiskLimit(Base):
    __tablename__ = "risk_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    max_order_notional: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    max_position_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    max_daily_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    max_open_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    portfolio = relationship("Portfolio", back_populates="risk_limit")
