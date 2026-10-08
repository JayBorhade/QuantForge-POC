"""Canonical order lifecycle and broker-status mapping."""

from sqlalchemy import select
from app.models.order import Order, OrderStatus
from app.services.audit import log_audit
from app.services.fill_accounting import FillService, FillAccountingError


_TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.FAILED,
}


class OrderStatusMapper:
    """Translate broker statuses into internal order states."""

    _MAP = {
        "pending": OrderStatus.PENDING,
        "submitted": OrderStatus.SUBMITTED,
        "accepted": OrderStatus.SUBMITTED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "partial": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "cancelled": OrderStatus.CANCELLED,
        "canceled": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
        "failed": OrderStatus.FAILED,
    }

    @classmethod
    def from_broker_status(cls, status: str) -> OrderStatus:
        normalized = status.strip().lower()
        if normalized not in cls._MAP:
            raise ValueError(f"Unsupported broker order status: {status!r}")
        return cls._MAP[normalized]


class OrderLifecycleService:
    """Enforce safe state transitions and canonical cancellation semantics."""

    def __init__(self, db, broker):
        self.db = db
        self.broker = broker

    async def cancel(self, order: Order) -> Order:
        result = await self.db.execute(
            select(Order).where(Order.id == order.id).with_for_update()
        )
        locked = result.scalar_one_or_none()
        if locked is None:
            raise ValueError("Order not found")
        if locked.status in _TERMINAL_STATUSES:
            raise ValueError(f"Cannot cancel terminal order: {locked.status.value}")
        if not locked.broker_order_id:
            raise ValueError("Cannot cancel an order without a broker order id")
        await self.broker.cancel_order(locked.broker_order_id)
        locked.status = OrderStatus.CANCELLED
        await log_audit(
            self.db,
            action="order.cancelled",
            resource="order",
            resource_id=str(locked.id),
            details={"broker_order_id": locked.broker_order_id},
        )
        await self.db.flush()
        return locked

    async def reconcile_open_orders(self) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(
                Order.status.in_(
                    (OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED)
                ),
                Order.broker_order_id.is_not(None),
            )
        )
        orders = list(result.scalars().all())
        for order in orders:
            await self.reconcile(order)
        return orders

    async def reconcile(self, order: Order) -> Order:
        result = await self.db.execute(
            select(Order).where(Order.id == order.id).with_for_update()
        )
        locked = result.scalar_one_or_none()
        if locked is None:
            raise ValueError("Order not found")
        if not locked.broker_order_id:
            raise ValueError("Cannot reconcile an order without a broker order id")
        broker_result = await self.broker.get_order(locked.broker_order_id)
        previous_filled = locked.filled_quantity
        broker_filled = broker_result.filled_quantity
        if broker_filled < previous_filled:
            raise ValueError("Broker reconciliation attempted to regress cumulative fill quantity")
        if broker_filled > previous_filled:
            if broker_result.average_fill_price is None or broker_result.average_fill_price <= 0:
                raise ValueError("Broker reported additional quantity without a valid average fill price")
            delta_quantity = broker_filled - previous_filled
            fill_key = f"broker:{locked.broker_order_id}:filled:{broker_filled}"
            try:
                await FillService(self.db).apply_fill(
                    order_id=locked.id,
                    quantity=delta_quantity,
                    price=broker_result.average_fill_price,
                    broker_fill_id=fill_key,
                )
            except FillAccountingError as exc:
                raise ValueError(f"Broker fill accounting failed: {exc}") from exc
        new_status = OrderStatusMapper.from_broker_status(broker_result.status)
        previous_status = locked.status
        if previous_status is OrderStatus.FILLED and new_status is not OrderStatus.FILLED:
            raise ValueError("Broker reconciliation attempted to regress a filled order")
        if previous_status is OrderStatus.CANCELLED and new_status is not OrderStatus.CANCELLED:
            raise ValueError("Broker reconciliation attempted to regress a cancelled order")
        if new_status is OrderStatus.FILLED and locked.filled_quantity != locked.quantity:
            raise ValueError("Broker reports filled order before local fill accounting is complete")
        locked.status = new_status
        if new_status is OrderStatus.REJECTED:
            locked.rejection_reason = broker_result.status[:512]
        if new_status is not previous_status:
            await log_audit(
                self.db,
                action="order.reconciled",
                resource="order",
                resource_id=str(locked.id),
                details={
                    "previous_status": previous_status.value,
                    "new_status": new_status.value,
                    "broker_order_id": locked.broker_order_id,
                },
            )
        await self.db.flush()
        return locked
