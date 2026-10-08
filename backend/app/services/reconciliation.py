"""Conservative reconciliation helpers for stale and uncertain broker orders."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerAdapter, BrokerSubmissionUnknown
from app.models.order import Order, OrderStatus
from app.services.audit import log_audit
from app.services.order_lifecycle import OrderLifecycleService, OrderStatusMapper


class ReconciliationService:
    """Reconcile broker orders without issuing duplicate submissions."""

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
                Order.updated_at <= cutoff,
            )
        )
        orders = list(result.scalars().all())
        return [await self.lifecycle.reconcile(order) for order in orders]

    async def reconcile_uncertain_submissions(self) -> list[Order]:
        """Resolve unknown submissions only when the broker can prove an order exists.

        An unresolved order deliberately remains SUBMISSION_UNKNOWN. This method never
        resubmits an order merely because a lookup returned no match.
        """
        result = await self.db.execute(
            select(Order).where(Order.status == OrderStatus.SUBMISSION_UNKNOWN)
        )
        orders = list(result.scalars().all())
        resolved: list[Order] = []
        finder = getattr(self.lifecycle.broker, "find_order_by_client_order_id", None)
        if finder is None:
            return orders

        for order in orders:
            try:
                broker_result = await finder(order.client_order_id, order.symbol)
            except BrokerSubmissionUnknown:
                continue
            if broker_result is None:
                continue

            previous_status = order.status
            new_status = OrderStatusMapper.from_broker_status(broker_result.status)
            order.broker_order_id = broker_result.broker_order_id
            order.status = new_status
            if new_status is OrderStatus.REJECTED:
                order.rejection_reason = broker_result.status[:512]
            await log_audit(
                self.db,
                action="order.submission_reconciled",
                resource="order",
                resource_id=str(order.id),
                details={
                    "previous_status": previous_status.value,
                    "new_status": new_status.value,
                    "broker_order_id": broker_result.broker_order_id,
                },
            )
            resolved.append(order)

        await self.db.flush()
        return resolved
