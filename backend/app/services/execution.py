"""Execution service with paper/live safety boundaries."""

from decimal import Decimal
from typing import Mapping
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ExecutionMode, Order, OrderSide, OrderStatus, OrderType
from app.brokers.base import BrokerOrderRequest, BrokerAdapter, BrokerSubmissionUnknown, BrokerSubmissionRejected
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.risk import RiskRejected, RiskService
from app.services.order_lifecycle import OrderStatusMapper
from app.services.audit import log_audit


class ExecutionService:
    def __init__(self, db: AsyncSession, broker: BrokerAdapter | None = None):
        self.db = db
        self.broker = broker

    @staticmethod
    def _matches_existing_request(
        order: Order,
        *,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        mode: ExecutionMode,
        strategy_id: UUID | None,
        order_type: OrderType,
        limit_price: Decimal | None,
    ) -> bool:
        return (
            order.symbol == symbol.strip().upper()
            and order.side is side
            and order.quantity == quantity
            and order.mode is mode
            and order.strategy_id == strategy_id
            and order.order_type is order_type
            and order.limit_price == limit_price
        )

    async def submit(
        self,
        *,
        portfolio: Portfolio,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        mode: ExecutionMode,
        client_order_id: str,
        strategy_id: UUID | None = None,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Decimal | None = None,
        estimated_price: Decimal | None = None,
        broker_params: Mapping[str, str] | None = None,
    ) -> Order:
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("Order quantity must be finite and positive")
        for label, price in (("limit_price", limit_price), ("estimated_price", estimated_price)):
            if price is not None and (not price.is_finite() or price <= 0):
                raise ValueError(f"{label} must be finite and positive")
        if not symbol.strip():
            raise ValueError("Order symbol is required")
        if not client_order_id or len(client_order_id) > 64:
            raise ValueError("client_order_id must contain 1 to 64 characters")
        if mode is ExecutionMode.LIVE:
            if self.broker is None:
                raise ValueError("Live execution requires an approved broker executor")
            user_result = await self.db.execute(select(User).where(User.id == portfolio.user_id))
            owner = user_result.scalar_one_or_none()
            if owner is None or not owner.is_verified:
                raise ValueError("Live execution requires a verified account")
            if not owner.two_factor_enabled:
                raise ValueError("Live execution requires two-factor authentication")

        existing = await self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio.id,
                Order.client_order_id == client_order_id,
            )
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            if not self._matches_existing_request(
                duplicate, symbol=symbol, side=side, quantity=quantity, mode=mode,
                strategy_id=strategy_id, order_type=order_type, limit_price=limit_price,
            ):
                raise ValueError("client_order_id has already been used for a different order")
            return duplicate

        risk_price = estimated_price if estimated_price is not None else limit_price
        if mode is ExecutionMode.LIVE and risk_price is None:
            raise ValueError(
                "Live execution requires an estimated price for pre-trade risk checks"
            )

        normalized_symbol = symbol.strip().upper()
        # Serialize order admission per portfolio for the duration of the
        # transaction. This prevents concurrent requests from both passing
        # risk checks against the same stale exposure snapshot.
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:portfolio_id))"),
            {"portfolio_id": str(portfolio.id)},
        )
        # Re-check idempotency after acquiring the portfolio lock. A competing
        # request may have committed the same client ID while this request
        # waited for the lock.
        duplicate_after_lock = await self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio.id,
                Order.client_order_id == client_order_id,
            )
        )
        existing_after_lock = duplicate_after_lock.scalar_one_or_none()
        if existing_after_lock is not None:
            if not self._matches_existing_request(
                existing_after_lock, symbol=symbol, side=side, quantity=quantity, mode=mode,
                strategy_id=strategy_id, order_type=order_type, limit_price=limit_price,
            ):
                raise ValueError("client_order_id has already been used for a different order")
            return existing_after_lock

        try:
            await RiskService(self.db).require_approval(
                portfolio=portfolio,
                symbol=normalized_symbol,
                side=side,
                quantity=quantity,
                estimated_price=risk_price,
                strategy_id=strategy_id,
                require_limits=mode is ExecutionMode.LIVE,
            )
        except RiskRejected as exc:
            await log_audit(
                self.db,
                action="order.risk_rejected",
                resource="portfolio",
                resource_id=str(portfolio.id),
                details={
                    "symbol": normalized_symbol,
                    "side": side.value,
                    "quantity": str(quantity),
                    "reason": str(exc),
                    "strategy_id": str(strategy_id) if strategy_id else None,
                },
            )
            raise

        order = Order(
            portfolio_id=portfolio.id,
            strategy_id=strategy_id,
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

        # Commit the idempotency key before any broker network call. If the
        # process dies after the broker accepts the order, reconciliation still
        # has a durable local order to match against.
        await self.db.commit()
        await self.db.refresh(order)

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
        except (BrokerSubmissionUnknown, httpx.TransportError) as exc:
            order.status = OrderStatus.SUBMISSION_UNKNOWN
            order.rejection_reason = str(exc)[:512]
            await log_audit(
                self.db,
                action="order.submission_unknown",
                resource="order",
                resource_id=str(order.id),
                details={"error": str(exc)[:512], "mode": order.mode.value},
            )
            # Return normally so the request/task transaction commits the
            # SUBMISSION_UNKNOWN record. Raising here would roll it back and
            # erase the only durable idempotency key after an ambiguous send.
            await self.db.commit()
            return order
        except BrokerSubmissionRejected as exc:
            order.status = OrderStatus.FAILED
            order.rejection_reason = str(exc)[:512]
            await log_audit(
                self.db,
                action="order.execution_failed",
                resource="order",
                resource_id=str(order.id),
                details={"error": str(exc)[:512], "mode": order.mode.value},
            )
            await self.db.commit()
            raise
        except Exception as exc:
            # Unexpected post-submit errors can happen after a provider accepted
            # the request. Preserve the order as uncertain; never erase the
            # idempotency key or pretend it definitely failed.
            order.status = OrderStatus.SUBMISSION_UNKNOWN
            order.rejection_reason = str(exc)[:512]
            await log_audit(
                self.db,
                action="order.submission_unknown",
                resource="order",
                resource_id=str(order.id),
                details={"error_type": type(exc).__name__, "mode": order.mode.value},
            )
            await self.db.commit()
            return order

        return order
