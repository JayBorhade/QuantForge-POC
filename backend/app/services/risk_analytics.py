"""Derived portfolio risk analytics for dashboard and monitoring surfaces."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderSide, OrderStatus
from app.models.position import Position
from app.models.portfolio import Portfolio
from app.models.risk_limit import RiskLimit


@dataclass(frozen=True)
class RiskSummary:
    equity: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    open_order_notional: Decimal
    position_count: int
    open_order_count: int
    daily_pnl: Decimal
    kill_switch: bool
    gross_utilization: Decimal | None
    daily_loss_utilization: Decimal | None
    open_order_utilization: Decimal | None
    largest_symbol: str | None
    largest_symbol_exposure: Decimal
    largest_strategy_id: str | None
    largest_strategy_exposure: Decimal


class RiskAnalyticsService:
    OPEN_STATUSES = (
        OrderStatus.PENDING,
        OrderStatus.SUBMITTED,
        OrderStatus.SUBMISSION_UNKNOWN,
        OrderStatus.PARTIALLY_FILLED,
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def summarize(self, portfolio: Portfolio) -> RiskSummary:
        positions_result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = list(positions_result.scalars().all())

        orders_result = await self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio.id,
                Order.status.in_(self.OPEN_STATUSES),
            )
        )
        orders = list(orders_result.scalars().all())

        limits_result = await self.db.execute(
            select(RiskLimit).where(RiskLimit.portfolio_id == portfolio.id)
        )
        limits = limits_result.scalar_one_or_none()

        gross = sum(
            abs((p.quantity or Decimal("0")) * (p.average_cost or Decimal("0")))
            for p in positions
        )
        net = sum(
            (p.quantity or Decimal("0")) * (p.average_cost or Decimal("0"))
            for p in positions
        )
        open_notional = sum(
            (o.quantity - o.filled_quantity).copy_abs()
            * (o.limit_price or o.average_fill_price or Decimal("0"))
            for o in orders
        )

        symbol_exposure: dict[str, Decimal] = {}
        for p in positions:
            symbol_exposure[p.symbol] = abs(
                (p.quantity or Decimal("0")) * (p.average_cost or Decimal("0"))
            )
        for o in orders:
            notional = (
                (o.quantity - o.filled_quantity).copy_abs()
                * (o.limit_price or o.average_fill_price or Decimal("0"))
            )
            symbol_exposure[o.symbol] = symbol_exposure.get(o.symbol, Decimal("0")) + notional

        strategy_exposure: dict[str, Decimal] = {}
        for o in orders:
            if o.strategy_id is None:
                continue
            notional = (
                (o.quantity - o.filled_quantity).copy_abs()
                * (o.limit_price or o.average_fill_price or Decimal("0"))
            )
            key = str(o.strategy_id)
            strategy_exposure[key] = strategy_exposure.get(key, Decimal("0")) + notional

        largest_symbol, largest_symbol_exposure = (
            max(symbol_exposure.items(), key=lambda item: item[1])
            if symbol_exposure else (None, Decimal("0"))
        )
        largest_strategy_id, largest_strategy_exposure = (
            max(strategy_exposure.items(), key=lambda item: item[1])
            if strategy_exposure else (None, Decimal("0"))
        )

        equity = portfolio.total_value if portfolio.total_value > 0 else portfolio.cash_balance
        gross_utilization = (
            gross / limits.max_gross_exposure
            if limits and limits.max_gross_exposure and limits.max_gross_exposure > 0
            else None
        )
        daily_loss_utilization = (
            max(-portfolio.daily_pnl, Decimal("0")) / limits.max_daily_loss
            if limits and limits.max_daily_loss and limits.max_daily_loss > 0
            else None
        )
        open_order_utilization = (
            Decimal(len(orders)) / Decimal(limits.max_open_orders)
            if limits and limits.max_open_orders
            else None
        )

        return RiskSummary(
            equity=equity,
            gross_exposure=gross,
            net_exposure=net,
            open_order_notional=open_notional,
            position_count=len(positions),
            open_order_count=len(orders),
            daily_pnl=portfolio.daily_pnl,
            kill_switch=bool(limits.kill_switch) if limits else False,
            gross_utilization=gross_utilization,
            daily_loss_utilization=daily_loss_utilization,
            open_order_utilization=open_order_utilization,
            largest_symbol=largest_symbol,
            largest_symbol_exposure=largest_symbol_exposure,
            largest_strategy_id=largest_strategy_id,
            largest_strategy_exposure=largest_strategy_exposure,
        )
