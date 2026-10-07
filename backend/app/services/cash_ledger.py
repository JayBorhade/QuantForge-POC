"""Cash ledger service for auditable portfolio balance changes."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_ledger import CashLedgerEntry, CashLedgerType
from app.models.order import Order, OrderSide
from app.models.portfolio import Portfolio


class CashLedgerError(ValueError):
    """Raised when a cash ledger operation violates an invariant."""


class CashLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assert_balance_consistent(self, portfolio: Portfolio) -> None:
        result = await self.db.execute(
            select(CashLedgerEntry)
            .where(CashLedgerEntry.portfolio_id == portfolio.id)
            .order_by(CashLedgerEntry.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None:
            raise CashLedgerError("Portfolio has no cash ledger entries")
        if latest.balance_after != portfolio.cash_balance:
            raise CashLedgerError("Portfolio cash balance diverges from the cash ledger")

    async def record_trade_fill(
        self,
        *,
        portfolio: Portfolio,
        order: Order,
        fill_id,
        notional: Decimal,
        fee: Decimal,
    ) -> CashLedgerEntry:
        if notional <= 0:
            raise CashLedgerError("Trade notional must be positive")
        if fee < 0:
            raise CashLedgerError("Trade fee cannot be negative")

        amount = (
            -(notional + fee)
            if order.side is OrderSide.BUY
            else notional - fee
        )
        key = f"fill:{fill_id}"

        existing = await self.db.execute(
            select(CashLedgerEntry).where(
                CashLedgerEntry.idempotency_key == key
            )
        )
        entry = existing.scalar_one_or_none()
        if entry is not None:
            return entry

        entry = CashLedgerEntry(
            portfolio_id=portfolio.id,
            entry_type=CashLedgerType.TRADE,
            amount=amount,
            balance_after=portfolio.cash_balance,
            idempotency_key=key,
            order_id=order.id,
            execution_fill_id=fill_id,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
