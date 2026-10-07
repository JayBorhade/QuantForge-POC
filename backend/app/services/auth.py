"""Authentication service."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple

import pyotp
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from user_agents import parse as parse_ua

from app.core.config import get_settings
from app.core.sanitize import sanitize_email, sanitize_phone, sanitize_string
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_otp,
    generate_token,
    hash_password,
    verify_password,
)
from app.models.notification import Notification, NotificationType
from app.models.portfolio import Portfolio
from app.models.session import UserSession
from app.models.subscription import PlanTier, Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.services.audit import log_audit

settings = get_settings()


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: SignupRequest, request: Request) -> User:
        email = sanitize_email(data.email)
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user = User(
            email=email,
            full_name=sanitize_string(data.full_name, 255) or data.full_name,
            phone=sanitize_phone(data.phone) if data.phone else None,
            hashed_password=hash_password(data.password),
            email_verification_token=generate_token(),
        )
        db.add(user)
        await db.flush()

        subscription = Subscription(
            user_id=user.id,
            plan=PlanTier.FREE,
            status=SubscriptionStatus.TRIAL,
        )
        db.add(subscription)

        portfolio = Portfolio(
            user_id=user.id,
            name="Main Portfolio",
            total_value=Decimal("100000"),
            cash_balance=Decimal("100000"),
        )
        db.add(portfolio)

        welcome = Notification(
            user_id=user.id,
            type=NotificationType.SYSTEM,
            title="Welcome to QuantForge",
            message="Your account is ready. Create a strategy and run your first backtest.",
        )
        db.add(welcome)

        await log_audit(
            db,
            action="user.register",
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return user

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        email: str,
        password: str,
        remember_me: bool,
        request: Request,
        otp_code: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        email = sanitize_email(email)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if user.is_banned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

        if user.two_factor_enabled:
            if not otp_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA code required")
            totp = pyotp.TOTP(user.two_factor_secret)
            if not totp.verify(otp_code, valid_window=1):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

        jti = generate_token()[:32]
        access_token = create_access_token(str(user.id), {"role": user.role.value})
        refresh_token = create_refresh_token(str(user.id), jti)

        ua_string = request.headers.get("user-agent", "")
        ua = parse_ua(ua_string)
        expires_days = settings.refresh_token_expire_days if remember_me else 1

        session = UserSession(
            user_id=user.id,
            refresh_token_jti=jti,
            device_name=f"{ua.browser.family} on {ua.os.family}",
            device_type=ua.device.family,
            ip_address=request.client.host if request.client else None,
            user_agent=ua_string[:500],
            remember_me=remember_me,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
        )
        db.add(session)

        user.last_login = datetime.now(timezone.utc)
        await log_audit(
            db,
            action="user.login",
            user_id=user.id,
            ip_address=session.ip_address,
            user_agent=ua_string,
        )
        return user, access_token, refresh_token

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession,
        refresh_token: str,
        request: Request,
    ) -> Tuple[str, str]:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        jti = payload.get("jti")
        user_id = payload.get("sub")

        result = await db.execute(
            select(UserSession).where(
                UserSession.refresh_token_jti == jti,
                UserSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if not session or session.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

        session.is_active = False
        new_jti = generate_token()[:32]
        new_refresh = create_refresh_token(user_id, new_jti)
        new_access = create_access_token(user_id)

        ua_string = request.headers.get("user-agent", "")
        ua = parse_ua(ua_string)
        new_session = UserSession(
            user_id=uuid.UUID(user_id),
            refresh_token_jti=new_jti,
            device_name=session.device_name,
            device_type=session.device_type,
            ip_address=request.client.host if request.client else None,
            user_agent=ua_string[:500],
            remember_me=session.remember_me,
            expires_at=session.expires_at,
        )
        db.add(new_session)
        session.last_used_at = datetime.now(timezone.utc)

        return new_access, new_refresh

    @staticmethod
    async def logout(db: AsyncSession, user_id: uuid.UUID, jti: Optional[str] = None) -> None:
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
        )
        if jti:
            query = query.where(UserSession.refresh_token_jti == jti)

        result = await db.execute(query)
        for session in result.scalars().all():
            session.is_active = False

        await log_audit(db, action="user.logout", user_id=user_id)

    @staticmethod
    def setup_2fa(user: User) -> Tuple[str, str]:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="QuantForge")
        return secret, uri
