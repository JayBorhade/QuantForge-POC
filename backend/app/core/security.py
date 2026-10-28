"""Security utilities: JWT, password hashing, tokens."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


_PASSWORD_HASH_PREFIX = "bcrypt-72$"


def _password_material(password: str) -> bytes:
    material = password.encode("utf-8")
    if len(material) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return material


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_password_material(password), bcrypt.gensalt()).decode("utf-8")
    return f"{_PASSWORD_HASH_PREFIX}{hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith(_PASSWORD_HASH_PREFIX):
            material = _password_material(plain_password)
            encoded_hash = hashed_password[len(_PASSWORD_HASH_PREFIX):]
        else:
            # Existing bcrypt hashes remain verifiable and are upgraded at login.
            material = plain_password.encode("utf-8")[:72]
            encoded_hash = hashed_password
        return bcrypt.checkpw(material, encoded_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def needs_password_rehash(hashed_password: str) -> bool:
    return not hashed_password.startswith(_PASSWORD_HASH_PREFIX)


def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Create an access token while protecting its standard claims from overrides."""
    payload: Dict[str, Any] = dict(extra or {})
    payload.update(
        {
            "sub": subject,
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.access_token_expire_minutes),
            "type": "access",
        }
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, jti: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_one_time_token(token: str) -> str:
    """Key password-reset and email-verification digests before database storage."""
    return hmac.new(settings.jwt_secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"
