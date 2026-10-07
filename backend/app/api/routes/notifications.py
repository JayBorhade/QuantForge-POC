"""Notification routes."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DbSession
from app.models.notification import Notification, NotificationType

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
    limit: int = 50,
):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [
        NotificationResponse(
            id=n.id,
            type=n.type.value,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in result.scalars().all()
    ]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_read(current_user: CurrentUser, db: DbSession):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    return {"message": "All notifications marked as read"}
