"""Celery tasks for safe broker order reconciliation."""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select, text

from app.brokers.factory import get_broker_adapter
from app.celery_app import celery_app
from app.core.encryption import decrypt_credentials
from app.db.session import AsyncSessionLocal
from app.models.broker_token import BrokerToken
from app.models.order import ExecutionMode, Order, OrderStatus
from app.models.portfolio import Portfolio
from app.services.order_lifecycle import OrderLifecycleService

logger = logging.getLogger(__name__)

_OPEN_STATUSES = (
    OrderStatus.PENDING,
    OrderStatus.SUBMITTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.SUBMISSION_UNKNOWN,
)
_RECONCILIATION_LOCK = "quantforge.order.reconciliation"


async def _reconcile_order(db, order_id: uuid.UUID) -> dict:
    """Reconcile one order using its owner's active broker credentials."""
    result = await db.execute(
        select(Order, Portfolio, BrokerToken)
        .join(Portfolio, Order.portfolio_id == Portfolio.id)
        .join(
            BrokerToken,
            (BrokerToken.user_id == Portfolio.user_id)
            & (BrokerToken.is_active.is_(True))
            & (BrokerToken.broker == Portfolio.broker),
        )
        .where(Order.id == order_id)
    )
    row = result.first()
    if row is None:
        return {"order_id": str(order_id), "status": "skipped", "reason": "broker_not_configured"}

    order, portfolio, token = row
    credentials = decrypt_credentials(token.api_secret_encrypted)
    adapter = get_broker_adapter(
        token.broker.value,
        credentials["api_key"],
        credentials["api_secret"],
        credentials.get("access_token"),
    )

    if order.status is OrderStatus.SUBMISSION_UNKNOWN:
        broker_result = await adapter.find_order_by_client_order_id(
            order.client_order_id,
            order.symbol,
        )
        if broker_result is None:
            logger.info("Unresolved uncertain broker submission %s", order.id)
            return {"order_id": str(order.id), "status": "unresolved"}

        order.broker_order_id = broker_result.broker_order_id
        order.status = OrderStatus.SUBMITTED
        await db.flush()

    reconciled = await OrderLifecycleService(db, adapter).reconcile(order)
    return {
        "order_id": str(reconciled.id),
        "status": reconciled.status.value,
        "filled_quantity": str(reconciled.filled_quantity),
    }


@celery_app.task(bind=True, max_retries=0, ignore_result=False)
def reconcile_broker_orders(self):
    """Reconcile all open live orders without aborting the sweep on one failure."""
    async def _run():
        async with AsyncSessionLocal() as db:
            dialect = db.bind.dialect.name if db.bind is not None else ""
            if dialect == "postgresql":
                acquired = (
                    await db.execute(
                        text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
                        {"key": _RECONCILIATION_LOCK},
                    )
                ).scalar()
                if not acquired:
                    return {
                        "reconciled": 0,
                        "failed": 0,
                        "unresolved": 0,
                        "skipped": 0,
                        "locked": True,
                    }

            result = await db.execute(
                select(Order.id)
                .where(
                    Order.mode == ExecutionMode.LIVE,
                    Order.status.in_(_OPEN_STATUSES),
                )
                .order_by(Order.created_at.asc())
            )
            order_ids = [row[0] for row in result.all()]
            summary = {
                "reconciled": 0,
                "failed": 0,
                "unresolved": 0,
                "skipped": 0,
                "locked": False,
            }

            for order_id in order_ids:
                try:
                    async with db.begin_nested():
                        item = await _reconcile_order(db, order_id)
                    status = item["status"]
                    if status == "unresolved":
                        summary["unresolved"] += 1
                    elif status == "skipped":
                        summary["skipped"] += 1
                    else:
                        summary["reconciled"] += 1
                except Exception as exc:
                    summary["failed"] += 1
                    logger.exception("Broker reconciliation failed for order %s: %s", order_id, exc)

            await db.commit()
            logger.info("Broker reconciliation sweep completed: %s", summary)
            return summary

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=0, ignore_result=False)
def reconcile_broker_order(self, order_id: str):
    """Reconcile one live order for targeted operational recovery."""
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
            order = result.scalar_one_or_none()
            if order is None:
                return {"order_id": order_id, "status": "skipped", "reason": "not_found"}
            if order.mode is not ExecutionMode.LIVE:
                return {"order_id": order_id, "status": "skipped", "reason": "not_live"}
            if order.status not in _OPEN_STATUSES:
                return {"order_id": order_id, "status": "skipped", "reason": "terminal"}

            item = await _reconcile_order(db, order.id)
            await db.commit()
            return item

    return asyncio.run(_run())
