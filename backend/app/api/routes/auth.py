"""Authentication routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.csrf import set_csrf_cookie
from app.core.encryption import decrypt_mfa_secret, encrypt_mfa_secret
from app.core.security import decode_token, generate_token, hash_password
from app.core.rate_limit import limiter
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
    cookie_options = {
        "domain": settings.cookie_domain,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    response.delete_cookie("access_token", path="/", httponly=True, **cookie_options)
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh", httponly=True, **cookie_options)
    response.delete_cookie("csrf_token", path="/", httponly=False, **cookie_options)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
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
@limiter.limit("5/minute")
async def login(data: LoginRequest, request: Request, response: Response, db: DbSession):
    user, access_token, refresh_token = await AuthService.authenticate(
        db, data.email, data.password, data.remember_me, request, data.otp_code
    )
    set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(expires_in=settings.access_token_expire_minutes * 60)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    access_token, new_refresh = await AuthService.refresh_tokens(db, token, request)
    set_auth_cookies(response, access_token, new_refresh)
    return TokenResponse(expires_in=settings.access_token_expire_minutes * 60)


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
    # Close already-established sockets as well as invalidating future requests.
    from app.api.routes.websocket import manager
    await manager.disconnect_user(str(current_user.id))
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.post("/forgot-password")
@limiter.limit("3/minute")
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
@limiter.limit("5/minute")
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
    # A password reset is a credential-compromise boundary: invalidate every
    # refresh session so old refresh tokens cannot mint new access tokens.
    # Already-issued access tokens remain valid only until their short expiry.
    await AuthService.revoke_sessions(db, user.id)
    from app.api.routes.websocket import manager
    await manager.disconnect_user(str(user.id))
    await log_audit(db, action="user.reset_password", user_id=user.id)
    return {"message": "Password reset successfully"}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    data: ForgotPasswordRequest,
    request: Request,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Resend verification without revealing whether an email is registered."""
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    if user and not user.is_verified:
        token = generate_token()
        user.email_verification_token = token
        background_tasks.add_task(send_verification_email, user.email, token)
    return {
        "message": "If the account exists and needs verification, a verification email has been sent"
    }


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(data: VerifyEmailRequest, request: Request, db: DbSession):
    result = await db.execute(select(User).where(User.email_verification_token == data.token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user.is_verified = True
    user.email_verification_token = None
    return {"message": "Email verified successfully"}


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
@limiter.limit("3/minute")
async def setup_2fa(request: Request, current_user: CurrentUser, db: DbSession):
    # Never silently replace a factor that is already protecting the account.
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="2FA is already enabled. Disable it with a valid OTP before setting up a new factor.",
        )
    secret, uri = AuthService.setup_2fa(current_user)
    current_user.two_factor_secret = encrypt_mfa_secret(secret)
    return TwoFactorSetupResponse(secret=secret, qr_uri=uri)


@router.post("/2fa/enable")
@limiter.limit("5/minute")
async def enable_2fa(data: TwoFactorVerifyRequest, request: Request, current_user: CurrentUser, db: DbSession):
    import pyotp

    if not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setup 2FA first")

    totp = pyotp.TOTP(decrypt_mfa_secret(current_user.two_factor_secret))
    if not totp.verify(data.otp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    current_user.two_factor_enabled = True
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def disable_2fa(data: TwoFactorVerifyRequest, request: Request, current_user: CurrentUser, db: DbSession):
    import pyotp

    if not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not configured")
    totp = pyotp.TOTP(decrypt_mfa_secret(current_user.two_factor_secret))
    if not totp.verify(data.otp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    return {"message": "2FA disabled successfully"}
