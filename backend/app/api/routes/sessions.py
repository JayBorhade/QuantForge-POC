"""User session management routes."""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.session import UserSession

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class SessionResponse(BaseModel):
    id: uuid.UUID
    device_name: str | None
    device_type: str | None
    ip_address: str | None
    last_used_at: str
    is_active: bool
    remember_me: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=List[SessionResponse])
async def list_sessions(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == current_user.id, UserSession.is_active == True)
        .order_by(UserSession.last_used_at.desc())
    )
    sessions = result.scalars().all()
    return [
        SessionResponse(
            id=s.id,
            device_name=s.device_name,
            device_type=s.device_type,
            ip_address=s.ip_address,
            last_used_at=s.last_used_at.isoformat(),
            is_active=s.is_active,
            remember_me=s.remember_me,
        )
        for s in sessions
    ]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.is_active = False
