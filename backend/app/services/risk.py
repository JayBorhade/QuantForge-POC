"""Deterministic pre-trade risk checks."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderSide, OrderStatus
from app.models.position import Position
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.risk_limit import RiskLimit


class RiskRejected(ValueError):
    """Raised when an order violates a configured portfolio risk limit."""


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str | None = None


class RiskService:
    """Single pre-trade policy gate. No broker/network calls belong here."""

    OPEN_STATUSES = (
        OrderStatus.PENDING,
        OrderStatus.SUBMITTED,
        OrderStatus.PARTIALLY_FILLED,
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        *,
        portfolio: Portfolio,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        estimated_price: Decimal | None = None,
    ) -> RiskDecision:
        if portfolio.status is not PortfolioStatus.ACTIVE:
            return RiskDecision(False, "Portfolio is not active")

        result = await self.db.execute(
            select(RiskLimit).where(RiskLimit.portfolio_id == portfolio.id)
        )
        limits = result.scalar_one_or_none()
        if limits is None:
            return RiskDecision(True)

        if limits.kill_switch:
            return RiskDecision(False, "Portfolio risk kill switch is enabled")

        if limits.max_daily_loss is not None and portfolio.daily_pnl <= -limits.max_daily_loss:
            return RiskDecision(False, "Maximum daily loss limit reached")

        if limits.max_open_orders is not None:
            open_count_result = await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.portfolio_id == portfolio.id,
                    Order.status.in_(self.OPEN_STATUSES),
                )
            )
            open_count = int(open_count_result.scalar_one())
            if open_count >= limits.max_open_orders:
                return RiskDecision(False, "Maximum open order limit reached")

        if limits.max_order_notional is not None:
            if estimated_price is None or estimated_price <= 0:
                return RiskDecision(False, "A positive estimated price is required for notional risk checks")
            if quantity * estimated_price > limits.max_order_notional:
                return RiskDecision(False, "Maximum order notional exceeded")

        if limits.max_position_quantity is not None:
            position_result = await self.db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.symbol == symbol,
                )
            )
            position = position_result.scalar_one_or_none()
            current_quantity = position.quantity if position else Decimal("0")
            projected_quantity = (
                current_quantity + quantity if side is OrderSide.BUY
                else current_quantity - quantity
            )
            if projected_quantity.copy_abs() > limits.max_position_quantity:
                return RiskDecision(False, "Maximum position quantity exceeded")

        return RiskDecision(True)

    async def require_approval(self, **kwargs) -> None:
        decision = await self.evaluate(**kwargs)
        if not decision.approved:
            raise RiskRejected(decision.reason or "Order rejected by risk policy")
