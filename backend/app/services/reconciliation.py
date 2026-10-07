"""Conservative reconciliation helpers for stale broker orders."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerAdapter
from app.models.order import Order, OrderStatus
from app.services.order_lifecycle import OrderLifecycleService


class ReconciliationService:
    """Reconcile aging open orders without issuing duplicate submissions."""

    def __init__(self, db: AsyncSession, broker: BrokerAdapter) -> None:
        self.db = db
        self.lifecycle = OrderLifecycleService(db, broker)

    async def reconcile_stale_orders(self, max_age_seconds: int = 300) -> list[Order]:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        result = await self.db.execute(
            select(Order).where(
                Order.status.in_((OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED)),
                Order.broker_order_id.is_not(None),
                Order.created_at <= cutoff,
            )
        )
        orders = list(result.scalars().all())
        return [await self.lifecycle.reconcile(order) for order in orders]
