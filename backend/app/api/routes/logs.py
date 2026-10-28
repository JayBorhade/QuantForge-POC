"""Strategy and system logs routes."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.strategy import Strategy, StrategyRun

router = APIRouter(prefix="/logs", tags=["Logs"])
logger = logging.getLogger("quantforge.logs")
settings = get_settings()


@router.get("/strategy")
async def strategy_logs(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(StrategyRun)
        .join(Strategy)
        .where(Strategy.user_id == current_user.id)
        .order_by(StrategyRun.created_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    logs = []
    for run in runs:
        # Provider/worker exception strings may contain URLs, account identifiers,
        # or secrets. Keep details in restricted server logs and expose a safe summary.
        message = (
            "Strategy run failed; inspect restricted server logs using the run ID."
            if run.error_message
            else f"Strategy run {run.status.value} — {run.mode.value} mode"
        )
        logs.append(
            {
                "timestamp": (run.started_at or run.created_at).isoformat(),
                "level": "ERROR" if run.error_message else "INFO",
                "message": message,
                "run_id": str(run.id),
                "metrics": {
                    "sharpe": float(run.sharpe_ratio) if run.sharpe_ratio else None,
                    "return": float(run.total_return) if run.total_return else None,
                },
            }
        )
    if not logs:
        logs = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "message": "QuantForge engine ready — no runs yet",
                "run_id": None,
            }
        ]
    return logs


@router.get("/audit")
async def user_audit_logs(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "resource": log.resource,
            "ip": log.ip_address,
        }
        for log in result.scalars().all()
    ]


async def _probe_database(db: AsyncSession) -> str:
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return "healthy"
    except Exception:
        logger.warning("System health probe failed for database")
        return "unavailable"


async def _probe_redis() -> str:
    client = None
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await asyncio.wait_for(client.ping(), timeout=1.25)
        return "healthy"
    except Exception:
        logger.warning("System health probe failed for Redis")
        return "unavailable"
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                logger.warning("Redis health probe client cleanup failed")


async def _probe_celery() -> str:
    try:
        from app.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1.0)
        response = await asyncio.wait_for(
            asyncio.to_thread(inspector.ping),
            timeout=1.5,
        )
        return "healthy" if response else "unavailable"
    except Exception:
        logger.warning("System health probe failed for Celery workers")
        return "unavailable"


@router.get("/system")
async def system_logs(current_user: CurrentUser, db: DbSession) -> list[dict[str, str]]:
    """Return bounded, live dependency probes instead of fabricated green statuses."""
    probes = await asyncio.gather(
        _probe_database(db),
        _probe_redis(),
        _probe_celery(),
    )
    now = datetime.now(timezone.utc).isoformat()
    services = ("database", "redis", "celery")
    return [
        {
            "timestamp": now,
            "level": "INFO" if state == "healthy" else "WARNING",
            "service": service,
            "status": state,
            "message": "Connection probe succeeded" if state == "healthy" else "Connection probe failed or no worker responded",
        }
        for service, state in zip(services, probes, strict=True)
    ]
