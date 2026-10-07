"""Transactional execution fill and position accounting."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_fill import ExecutionFill
from app.models.order import ExecutionMode, Order, OrderSide, OrderStatus
from app.models.portfolio import Portfolio
from app.models.position import Position


class FillAccountingError(ValueError):
    """Raised when a broker/paper fill violates execution invariants."""


class FillService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_fill(
        self,
        *,
        order_id,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
        broker_fill_id: str | None = None,
        executed_at: datetime | None = None,
    ) -> ExecutionFill:
        if quantity <= 0:
            raise FillAccountingError("Fill quantity must be positive")
        if price <= 0:
            raise FillAccountingError("Fill price must be positive")
        if fee < 0:
            raise FillAccountingError("Fill fee cannot be negative")

        # Lock order first so concurrent fills for one order serialize.
        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if order is None:
            raise FillAccountingError("Order not found")
        if order.status in {OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FAILED}:
            raise FillAccountingError("Cannot apply a fill to a terminal order")

        if broker_fill_id:
            existing_result = await self.db.execute(
                select(ExecutionFill).where(
                    ExecutionFill.order_id == order.id,
                    ExecutionFill.broker_fill_id == broker_fill_id,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                return existing

        remaining = order.quantity - order.filled_quantity
        if quantity > remaining:
            raise FillAccountingError("Fill quantity exceeds remaining order quantity")

        portfolio_result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == order.portfolio_id).with_for_update()
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if portfolio is None:
            raise FillAccountingError("Portfolio not found")

        position_result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == order.symbol,
            ).with_for_update()
        )
        position = position_result.scalar_one_or_none()

        notional = quantity * price
        if order.mode is ExecutionMode.PAPER:
            if order.side is OrderSide.BUY and portfolio.cash_balance < notional + fee:
                raise FillAccountingError("Insufficient paper cash for fill")
            if order.side is OrderSide.SELL and (position is None or position.quantity < quantity):
                raise FillAccountingError("Insufficient paper position for sell fill")

        if position is None:
            position = Position(
                portfolio_id=portfolio.id,
                symbol=order.symbol,
                quantity=Decimal("0"),
                average_cost=Decimal("0"),
                realized_pnl=Decimal("0"),
            )
            self.db.add(position)
            await self.db.flush()

        if order.side is OrderSide.BUY:
            old_qty = position.quantity
            new_qty = old_qty + quantity
            position.average_cost = (
                ((old_qty * position.average_cost) + (quantity * price)) / new_qty
                if new_qty else Decimal("0")
            )
            position.quantity = new_qty
        else:
            if position.quantity < quantity:
                raise FillAccountingError("Cannot sell more than the current position")
            position.realized_pnl += (price - position.average_cost) * quantity
            position.quantity -= quantity
            if position.quantity == 0:
                position.average_cost = Decimal("0")

        if order.mode is ExecutionMode.PAPER:
            if order.side is OrderSide.BUY:
                portfolio.cash_balance -= notional + fee
            else:
                portfolio.cash_balance += notional - fee

        fill = ExecutionFill(
            order_id=order.id,
            broker_fill_id=broker_fill_id,
            quantity=quantity,
            price=price,
            fee=fee,
            executed_at=executed_at or datetime.now(timezone.utc),
        )
        self.db.add(fill)

        previous_filled = order.filled_quantity
        order.filled_quantity = previous_filled + quantity
        order.average_fill_price = (
            ((previous_filled * (order.average_fill_price or Decimal("0"))) + (quantity * price))
            / order.filled_quantity
        )
        order.status = (
            OrderStatus.FILLED
            if order.filled_quantity == order.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        await self.db.flush()
        return fill
