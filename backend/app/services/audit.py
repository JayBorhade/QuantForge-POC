"""Audit logging service."""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[UUID] = None,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(entry)
    await db.flush()
