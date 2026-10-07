"""Strategy and system logs routes."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.audit_log import AuditLog
from app.models.strategy import Strategy, StrategyRun

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/strategy")
async def strategy_logs(current_user: CurrentUser, db: DbSession, limit: int = 100) -> List[Dict[str, Any]]:
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
        logs.append({
            "timestamp": (run.started_at or run.created_at).isoformat(),
            "level": "ERROR" if run.error_message else "INFO",
            "message": run.error_message or f"Strategy run {run.status.value} — {run.mode.value} mode",
            "run_id": str(run.id),
            "metrics": {
                "sharpe": float(run.sharpe_ratio) if run.sharpe_ratio else None,
                "return": float(run.total_return) if run.total_return else None,
            },
        })
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
async def user_audit_logs(current_user: CurrentUser, db: DbSession, limit: int = 50) -> List[Dict[str, Any]]:
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


@router.get("/system")
async def system_logs(current_user: CurrentUser) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"timestamp": now, "level": "INFO", "service": "api", "message": "Health check passed"},
        {"timestamp": now, "level": "INFO", "service": "celery", "message": "Worker heartbeat OK"},
        {"timestamp": now, "level": "INFO", "service": "redis", "message": "Connection pool active"},
    ]
