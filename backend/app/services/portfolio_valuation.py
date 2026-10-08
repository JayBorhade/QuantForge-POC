"""Authoritative mark-to-market portfolio valuation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select

from app.models.execution_fill import ExecutionFill
from app.models.order import ExecutionMode, Order
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.position import Position


class QuoteProvider(Protocol):
    async def get_quote(self, symbol: str, **kwargs) -> dict: ...


class PortfolioValuationError(ValueError):
    """Raised when a portfolio cannot be valued safely."""


@dataclass(frozen=True)
class PositionValuation:
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    portfolio_id: str
    cash_balance: Decimal
    position_market_value: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    gross_exposure: Decimal
    risk_exposure: Decimal
    positions: tuple[PositionValuation, ...]


class LatestExecutionQuoteProvider:
    """Provide deterministic marks from the latest execution in a portfolio."""

    def __init__(self, db: AsyncSession, portfolio_id, mode: ExecutionMode = ExecutionMode.PAPER):
        self.db = db
        self.portfolio_id = portfolio_id
        self.mode = mode

    async def get_quote(self, symbol: str, **kwargs) -> dict:
        result = await self.db.execute(
            select(ExecutionFill.price)
            .join(Order, Order.id == ExecutionFill.order_id)
            .where(
                Order.portfolio_id == self.portfolio_id,
                Order.mode == self.mode,
                Order.symbol == symbol,
            )
            .order_by(ExecutionFill.executed_at.desc(), ExecutionFill.id.desc())
            .limit(1)
        )
        price = result.scalar_one_or_none()
        if price is None:
            raise PortfolioValuationError(
                f"No execution mark is available for {symbol} in this portfolio"
            )
        return {"price": price, "source": "latest_execution"}


class PortfolioValuationService:
    """Calculate and optionally persist equity from cash, positions and market marks."""

    def __init__(self, db: AsyncSession, quote_provider: QuoteProvider):
        self.db = db
        self.quote_provider = quote_provider

    async def value_portfolio(self, portfolio: Portfolio, *, persist: bool = True) -> PortfolioValuation:
        result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id, Position.quantity != 0)
            .order_by(Position.symbol)
        )
        positions = list(result.scalars().all())
        valuations: list[PositionValuation] = []
        market_value = Decimal("0")
        realized_pnl = Decimal("0")

        for position in positions:
            quote = await self.quote_provider.get_quote(position.symbol)
            try:
                market_price = Decimal(str(quote["price"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise PortfolioValuationError(
                    f"Quote provider returned an invalid price for {position.symbol}"
                ) from exc
            if market_price <= 0:
                raise PortfolioValuationError(f"Market price must be positive for {position.symbol}")

            value = position.quantity * market_price
            unrealized = (market_price - position.average_cost) * position.quantity
            market_value += value
            realized_pnl += position.realized_pnl
            valuations.append(
                PositionValuation(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    market_price=market_price,
                    market_value=value,
                    unrealized_pnl=unrealized,
                    realized_pnl=position.realized_pnl,
                )
            )

        equity = portfolio.cash_balance + market_value
        unrealized_pnl = sum((item.unrealized_pnl for item in valuations), Decimal("0"))
        total_pnl = realized_pnl + unrealized_pnl
        gross_exposure = market_value.copy_abs()
        risk_exposure = gross_exposure / equity if equity > 0 else Decimal("0")

        if persist:
            portfolio.total_value = equity
            portfolio.total_pnl = total_pnl
            portfolio.risk_exposure = risk_exposure
            await self.db.flush()

        return PortfolioValuation(
            portfolio_id=str(portfolio.id),
            cash_balance=portfolio.cash_balance,
            position_market_value=market_value,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            gross_exposure=gross_exposure,
            risk_exposure=risk_exposure,
            positions=tuple(valuations),
        )
