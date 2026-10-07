"""Authentication routes."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from jose import jwt
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.csrf import set_csrf_cookie
from app.core.security import decode_token, generate_token, hash_password
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import AuthService
from app.services.audit import log_audit
from app.services.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth/refresh",
    )
    set_csrf_cookie(response)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    response.delete_cookie("csrf_token", path="/")


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest, request: Request, db: DbSession, background_tasks: BackgroundTasks):
    user = await AuthService.register(db, data, request)
    if user.email_verification_token:
        background_tasks.add_task(
            send_verification_email,
            user.email,
            user.email_verification_token,
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, response: Response, db: DbSession):
    user, access_token, refresh_token = await AuthService.authenticate(
        db, data.email, data.password, data.remember_me, request, data.otp_code
    )
    set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
    refresh_token: Optional[str] = None,
):
    token = refresh_token or request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    access_token, new_refresh = await AuthService.refresh_tokens(db, token, request)
    set_auth_cookies(response, access_token, new_refresh)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
):
    refresh_token = request.cookies.get("refresh_token")
    jti = None
    if refresh_token:
        payload = decode_token(refresh_token)
        jti = payload.get("jti") if payload else None

    await AuthService.logout(db, current_user.id, jti)
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: DbSession, request: Request):
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    if user:
        token = generate_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await log_audit(db, action="user.forgot_password", user_id=user.id, ip_address=request.client.host if request.client else None)
        await send_password_reset_email(user.email, token)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: DbSession, request: Request):
    result = await db.execute(
        select(User).where(
            User.password_reset_token == data.token,
            User.password_reset_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user.hashed_password = hash_password(data.password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await log_audit(db, action="user.reset_password", user_id=user.id)
    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: DbSession):
    result = await db.execute(select(User).where(User.email_verification_token == data.token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user.is_verified = True
    user.email_verification_token = None
    return {"message": "Email verified successfully"}


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(current_user: CurrentUser, db: DbSession):
    secret, uri = AuthService.setup_2fa(current_user)
    current_user.two_factor_secret = secret
    return TwoFactorSetupResponse(secret=secret, qr_uri=uri)


@router.post("/2fa/enable")
async def enable_2fa(data: TwoFactorVerifyRequest, current_user: CurrentUser, db: DbSession):
    import pyotp

    if not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setup 2FA first")

    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(data.otp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    current_user.two_factor_enabled = True
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(data: TwoFactorVerifyRequest, current_user: CurrentUser, db: DbSession):
    import pyotp

    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(data.otp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    return {"message": "2FA disabled successfully"}
