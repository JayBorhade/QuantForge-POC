"""Deterministic paper execution orchestration."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerOrderRequest
from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.order import ExecutionMode, OrderSide
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
        fee: Decimal = Decimal("0"),
    ):
        order = await ExecutionService(self.db).submit(
            portfolio=portfolio,
            symbol=symbol,
            side=side,
            quantity=quantity,
            mode=ExecutionMode.PAPER,
            client_order_id=client_order_id,
        )

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
        if order.status.name == "REJECTED":
            raise ValueError("Paper broker rejected the order")
        await self.db.flush()

        fill = await FillService(self.db).apply_fill(
            order_id=order.id,
            quantity=quantity,
            price=fill_price,
            fee=fee,
            broker_fill_id=f"paper-fill:{client_order_id}",
        )
        return order, fill
