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
        OrderStatus.SUBMISSION_UNKNOWN,
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
        strategy_id=None,
    ) -> RiskDecision:
        if portfolio.status is not PortfolioStatus.ACTIVE:
            return RiskDecision(False, "Portfolio is not active")
        if quantity <= 0:
            return RiskDecision(False, "Order quantity must be positive")

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

        open_count_result = await self.db.execute(
            select(func.count(Order.id)).where(
                Order.portfolio_id == portfolio.id,
                Order.status.in_(self.OPEN_STATUSES),
            )
        )
        open_count = int(open_count_result.scalar_one())
        if limits.max_open_orders is not None and open_count >= limits.max_open_orders:
            return RiskDecision(False, "Maximum open order limit reached")

        if estimated_price is None or estimated_price <= 0:
            if any(
                value is not None
                for value in (
                    limits.max_order_notional,
                    limits.max_gross_exposure,
                    limits.max_symbol_exposure,
                    limits.max_strategy_exposure,
                    limits.max_strategy_allocation_pct,
                )
            ):
                return RiskDecision(False, "A positive estimated price is required for exposure risk checks")
            return RiskDecision(True)

        order_notional = quantity * estimated_price
        if limits.max_order_notional is not None and order_notional > limits.max_order_notional:
            return RiskDecision(False, "Maximum order notional exceeded")

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
        if limits.max_position_quantity is not None and projected_quantity.copy_abs() > limits.max_position_quantity:
            return RiskDecision(False, "Maximum position quantity exceeded")

        open_orders_result = await self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio.id,
                Order.status.in_(self.OPEN_STATUSES),
            )
        )
        open_orders = list(open_orders_result.scalars().all())

        current_gross = sum(
            abs((p.quantity or Decimal("0")) * (p.average_cost or Decimal("0")))
            for p in (await self._positions()).values()
        )
        open_gross = sum(
            (o.quantity - o.filled_quantity).copy_abs()
            * (o.limit_price or o.average_fill_price or estimated_price)
            for o in open_orders
        )
        projected_gross = current_gross + open_gross + order_notional
        if limits.max_gross_exposure is not None and projected_gross > limits.max_gross_exposure:
            return RiskDecision(False, "Maximum gross exposure exceeded")

        symbol_current = abs(current_quantity * (position.average_cost if position else estimated_price))
        symbol_open = sum(
            (o.quantity - o.filled_quantity).copy_abs()
            * (o.limit_price or o.average_fill_price or estimated_price)
            for o in open_orders if o.symbol == symbol
        )
        projected_symbol = symbol_current + symbol_open + order_notional
        if limits.max_symbol_exposure is not None and projected_symbol > limits.max_symbol_exposure:
            return RiskDecision(False, "Maximum symbol exposure exceeded")

        if strategy_id is not None and (
            limits.max_strategy_exposure is not None or limits.max_strategy_allocation_pct is not None
        ):
            strategy_open = sum(
                (o.quantity - o.filled_quantity).copy_abs()
                * (o.limit_price or o.average_fill_price or estimated_price)
                for o in open_orders if o.strategy_id == strategy_id
            )
            projected_strategy = strategy_open + order_notional
            if limits.max_strategy_exposure is not None and projected_strategy > limits.max_strategy_exposure:
                return RiskDecision(False, "Maximum strategy exposure exceeded")
            if limits.max_strategy_allocation_pct is not None:
                equity = portfolio.total_value if portfolio.total_value > 0 else portfolio.cash_balance
                if equity <= 0:
                    return RiskDecision(False, "Positive portfolio equity is required for strategy allocation checks")
                allocation = projected_strategy / equity
                if allocation > limits.max_strategy_allocation_pct:
                    return RiskDecision(False, "Maximum strategy allocation exceeded")

        return RiskDecision(True)

    async def _positions(self) -> dict:
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == self._portfolio_id)
        )
        return {p.symbol: p for p in result.scalars().all()}

    @property
    def _portfolio_id(self):
        return self._current_portfolio_id

    async def require_approval(self, **kwargs) -> None:
        self._current_portfolio_id = kwargs["portfolio"].id
        decision = await self.evaluate(**kwargs)
        if not decision.approved:
            raise RiskRejected(decision.reason or "Order rejected by risk policy")
