"""Bot deployment model."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus), default=DeploymentStatus.PENDING
    )
    region: Mapped[str] = mapped_column(String(64), default="us-east-1")
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
