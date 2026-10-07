"""User model."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.session import UserSession
    from app.models.strategy import Strategy
    from app.models.subscription import Subscription


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    strategies: Mapped[List["Strategy"]] = relationship(
        "Strategy", back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="user", uselist=False
    )
