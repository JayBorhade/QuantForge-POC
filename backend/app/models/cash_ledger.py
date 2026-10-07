"""Immutable portfolio cash ledger entries."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.execution_fill import ExecutionFill
    from app.models.order import Order
    from app.models.portfolio import Portfolio


class CashLedgerType(str, enum.Enum):
    OPENING_BALANCE = "opening_balance"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE = "trade"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class CashLedgerEntry(Base):
    __tablename__ = "cash_ledger_entries"
    __table_args__ = (
        Index("ix_cash_ledger_portfolio_created_at", "portfolio_id", "created_at"),
        Index("uq_cash_ledger_idempotency_key", "idempotency_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    entry_type: Mapped[CashLedgerType] = mapped_column(Enum(CashLedgerType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    execution_fill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("execution_fills.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio")
    order: Mapped[Optional["Order"]] = relationship("Order")
    execution_fill: Mapped[Optional["ExecutionFill"]] = relationship("ExecutionFill")
