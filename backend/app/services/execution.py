"""Execution service with paper/live safety boundaries."""

from decimal import Decimal
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ExecutionMode, Order, OrderSide, OrderStatus, OrderType
from app.brokers.base import BrokerOrderRequest, BrokerAdapter, BrokerSubmissionUnknown
from app.models.portfolio import Portfolio
from app.services.risk import RiskService
from app.services.order_lifecycle import OrderStatusMapper
from app.services.audit import log_audit


class ExecutionService:
    def __init__(self, db: AsyncSession, broker: BrokerAdapter | None = None):
        self.db = db
        self.broker = broker

    async def submit(
        self,
        *,
        portfolio: Portfolio,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        mode: ExecutionMode,
        client_order_id: str,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Decimal | None = None,
        broker_params: Mapping[str, str] | None = None,
    ) -> Order:
        if quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if not symbol.strip():
            raise ValueError("Order symbol is required")
        if mode is ExecutionMode.LIVE and self.broker is None:
            raise ValueError("Live execution requires an approved broker executor")

        existing = await self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio.id,
                Order.client_order_id == client_order_id,
            )
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            return duplicate

        normalized_symbol = symbol.strip().upper()

        await RiskService(self.db).require_approval(
            portfolio=portfolio,
            symbol=normalized_symbol,
            side=side,
            quantity=quantity,
            estimated_price=limit_price,
        )

        order = Order(
            portfolio_id=portfolio.id,
            symbol=normalized_symbol,
            side=side,
            order_type=order_type,
            mode=mode,
            quantity=quantity,
            limit_price=limit_price,
            client_order_id=client_order_id,
            status=OrderStatus.PENDING,
        )
        self.db.add(order)
        await self.db.flush()

        if mode is ExecutionMode.PAPER:
            order.status = OrderStatus.SUBMITTED
            return order

        order.status = OrderStatus.SUBMITTED
        try:
            result = await self.broker.submit_order(
                BrokerOrderRequest(
                    client_order_id=order.client_order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    limit_price=order.limit_price,
                    broker_params=dict(broker_params or {}),
                )
            )
            order.broker_order_id = result.broker_order_id
            order.status = OrderStatusMapper.from_broker_status(result.status)
            if order.status is OrderStatus.REJECTED:
                order.rejection_reason = result.status[:512]
            await log_audit(
                self.db,
                action="order.submitted",
                resource="order",
                resource_id=str(order.id),
                details={
                    "broker_order_id": order.broker_order_id,
                    "status": order.status.value,
                    "mode": order.mode.value,
                },
            )
        except BrokerSubmissionUnknown as exc:
            order.status = OrderStatus.SUBMISSION_UNKNOWN
            order.rejection_reason = str(exc)[:512]
            await log_audit(
                self.db,
                action="order.submission_unknown",
                resource="order",
                resource_id=str(order.id),
                details={"error": str(exc)[:512], "mode": order.mode.value},
            )
            await self.db.flush()
            raise
        except Exception as exc:
            order.status = OrderStatus.FAILED
            order.rejection_reason = str(exc)[:512]
            await log_audit(
                self.db,
                action="order.execution_failed",
                resource="order",
                resource_id=str(order.id),
                details={"error": str(exc)[:512], "mode": order.mode.value},
            )
            raise

        return order
