"""CSRF protection — double-submit cookie pattern."""

import secrets
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

# Paths exempt from CSRF (prefix match after /api/v1)
CSRF_EXEMPT_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/billing/webhook",
)

CSRF_EXEMPT_EXACT = ("/health", "/api/docs", "/api/openapi.json", "/api/redoc")


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def is_csrf_exempt(path: str) -> bool:
    if path in CSRF_EXEMPT_EXACT:
        return True
    if path.startswith("/api/v1/ws"):
        return True
    return any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES)


def validate_csrf(request: Request) -> None:
    settings = get_settings()
    if not settings.csrf_enabled:
        return

    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    path = request.url.path
    if is_csrf_exempt(path):
        return

    if not path.startswith(settings.api_v1_prefix):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)

    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


def set_csrf_cookie(response, token: Optional[str] = None) -> str:
    settings = get_settings()
    token = token or generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=86400 * 7,
        path="/",
    )
    return token
