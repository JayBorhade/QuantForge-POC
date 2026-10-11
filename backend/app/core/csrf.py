"""CSRF protection with a signed double-submit cookie."""
import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

# Exact endpoint exemptions prevent similarly named routes from bypassing CSRF.
CSRF_EXEMPT_SUFFIXES = frozenset({
    "/auth/login",
    "/auth/signup",
    "/auth/forgot-password",
    "/auth/resend-verification",
    "/auth/reset-password",
    "/auth/verify-email",
    "/billing/webhook",
})
CSRF_EXEMPT_EXACT = frozenset({"/health", "/health/ready", "/api/docs", "/api/openapi.json", "/api/redoc"})

def generate_csrf_token() -> str:
    raw = secrets.token_urlsafe(32)
    signature = hmac.new(get_settings().secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"

def is_csrf_exempt(path: str) -> bool:
    settings = get_settings()
    api_prefix = settings.api_v1_prefix.rstrip("/")
    exempt_paths = {f"{api_prefix}{suffix}" for suffix in CSRF_EXEMPT_SUFFIXES}
    if path in CSRF_EXEMPT_EXACT or path in exempt_paths:
        return True
    websocket_path = f"{api_prefix}/ws"
    return path == websocket_path or path.startswith(websocket_path + "/")

def _is_valid_signed_token(token: str) -> bool:
    try:
        raw, supplied_signature = token.rsplit(".", 1)
    except ValueError:
        return False
    if not raw or not supplied_signature:
        return False
    expected_signature = hmac.new(get_settings().secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied_signature, expected_signature)

def validate_csrf(request: Request) -> None:
    settings = get_settings()
    if not settings.csrf_enabled or request.method in ("GET", "HEAD", "OPTIONS"):
        return
    path = request.url.path
    if is_csrf_exempt(path) or not path.startswith(settings.api_v1_prefix + "/"):
        return
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token) or not _is_valid_signed_token(cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

def set_csrf_cookie(response, token: Optional[str] = None) -> str:
    settings = get_settings()
    token = token or generate_csrf_token()
    response.set_cookie(key=CSRF_COOKIE, value=token, httponly=False, secure=settings.cookie_secure, samesite=settings.cookie_samesite, domain=settings.cookie_domain, max_age=86400 * 7, path="/")
    return token
