"""Canonical order lifecycle and broker-status mapping."""

from app.models.order import Order, OrderStatus


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
        if order.status in _TERMINAL_STATUSES:
            raise ValueError(f"Cannot cancel terminal order: {order.status.value}")
        if not order.broker_order_id:
            raise ValueError("Cannot cancel an order without a broker order id")
        await self.broker.cancel_order(order.broker_order_id)
        order.status = OrderStatus.CANCELLED
        await self.db.flush()
        return order

    async def reconcile(self, order: Order) -> Order:
        if not order.broker_order_id:
            raise ValueError("Cannot reconcile an order without a broker order id")
        result = await self.broker.get_order(order.broker_order_id)
        new_status = OrderStatusMapper.from_broker_status(result.status)
        if order.status is OrderStatus.FILLED and new_status is not OrderStatus.FILLED:
            raise ValueError("Broker reconciliation attempted to regress a filled order")
        if order.status is OrderStatus.CANCELLED and new_status is not OrderStatus.CANCELLED:
            raise ValueError("Broker reconciliation attempted to regress a cancelled order")
        order.status = new_status
        if new_status is OrderStatus.REJECTED:
            order.rejection_reason = result.status[:512]
        await self.db.flush()
        return order
