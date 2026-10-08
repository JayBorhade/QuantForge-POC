"""Deterministic paper execution orchestration."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerOrderRequest
from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.execution_fill import ExecutionFill
from app.models.order import ExecutionMode, OrderSide, OrderStatus
from app.models.portfolio import Portfolio
from app.services.execution import ExecutionService
from app.services.fill_accounting import FillService
from app.services.order_lifecycle import OrderStatusMapper


class PaperExecutionService:
    """Submit a paper order, acknowledge it, then apply its deterministic fill."""

    def __init__(
        self,
        db: AsyncSession,
        broker: PaperBrokerAdapter | None = None,
    ) -> None:
        self.db = db
        self.broker = broker or PaperBrokerAdapter()

    async def execute(
        self,
        *,
        portfolio: Portfolio,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        client_order_id: str,
        fill_price: Decimal,
        strategy_id: UUID | None = None,
        fee: Decimal = Decimal("0"),
    ):
        order = await ExecutionService(self.db).submit(
            portfolio=portfolio,
            symbol=symbol,
            side=side,
            quantity=quantity,
            mode=ExecutionMode.PAPER,
            client_order_id=client_order_id,
            strategy_id=strategy_id,
            estimated_price=fill_price,
        )

        paper_fill_id = f"paper-fill:{client_order_id}"
        if order.status is OrderStatus.FILLED:
            existing_result = await self.db.execute(
                select(ExecutionFill).where(
                    ExecutionFill.order_id == order.id,
                    ExecutionFill.broker_fill_id == paper_fill_id,
                )
            )
            existing_fill = existing_result.scalar_one_or_none()
            if existing_fill is None:
                raise ValueError("Filled paper order is missing its execution fill")
            return order, existing_fill

        if order.status in {OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FAILED}:
            raise ValueError(f"Cannot replay terminal paper order: {order.status.value}")

        broker_result = await self.broker.submit_order(
            BrokerOrderRequest(
                client_order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                limit_price=order.limit_price,
            )
        )
        order.broker_order_id = broker_result.broker_order_id
        order.status = OrderStatusMapper.from_broker_status(broker_result.status)
        if order.status is OrderStatus.REJECTED:
            raise ValueError("Paper broker rejected the order")
        await self.db.flush()

        fill = await FillService(self.db).apply_fill(
            order_id=order.id,
            quantity=quantity,
            price=fill_price,
            fee=fee,
            broker_fill_id=paper_fill_id,
        )
        return order, fill
