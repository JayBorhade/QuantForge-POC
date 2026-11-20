"""Admin panel routes."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentAdmin, DbSession
from app.models.audit_log import AuditLog
from app.models.strategy import Strategy, StrategyStatus
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
async def list_users(
    admin: CurrentAdmin,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "is_banned": u.is_banned,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: UUID, admin: CurrentAdmin, db: DbSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_banned = True
    user.is_active = False
    return {"message": "User banned"}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: UUID, admin: CurrentAdmin, db: DbSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_banned = False
    user.is_active = True
    return {"message": "User unbanned"}


@router.get("/analytics")
async def get_analytics(admin: CurrentAdmin, db: DbSession) -> Dict[str, Any]:
    users_count = await db.execute(select(func.count(User.id)))
    active_users = await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
    subs = await db.execute(select(func.count(Subscription.id)))
    active_strategies = await db.execute(
        select(func.count(Strategy.id)).where(Strategy.status == StrategyStatus.ACTIVE)
    )

    return {
        "total_users": users_count.scalar() or 0,
        "active_users": active_users.scalar() or 0,
        "subscriptions": subs.scalar() or 0,
        "api_requests_24h": None,
        "api_request_metrics_available": False,
        "active_strategies": active_strategies.scalar() or 0,
        "server_status": "database_connected",
    }


@router.get("/audit-logs")
async def get_audit_logs(
    admin: CurrentAdmin,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> List[Dict]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource": log.resource,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
