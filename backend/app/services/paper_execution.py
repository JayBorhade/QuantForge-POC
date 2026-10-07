"""Deterministic paper execution orchestration."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.order import ExecutionMode, Order, OrderSide, OrderStatus
from app.models.portfolio import Portfolio
from app.services.execution import ExecutionService
from app.services.fill_accounting import FillService


class PaperExecutionService:
    """Submit a paper order and apply an explicit deterministic fill.

    The fill price is supplied by the caller/simulation clock. No market data
    or network dependency is introduced into the paper execution path.
    """

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
        order = await ExecutionService(self.db, self.broker).submit(
            portfolio=portfolio,
            symbol=symbol,
            side=side,
            quantity=quantity,
            mode=ExecutionMode.LIVE,
            client_order_id=client_order_id,
        )

        if order.status is OrderStatus.CANCELLED:
            return order, None

        fill = await FillService(self.db).apply_fill(
            order_id=order.id,
            quantity=quantity,
            price=fill_price,
            fee=fee,
            broker_fill_id=f"paper-fill:{client_order_id}",
        )
        return order, fill
