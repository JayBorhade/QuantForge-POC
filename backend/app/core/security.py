"""Security utilities: JWT, password hashing, tokens."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


_PASSWORD_HASH_PREFIX = "bcrypt-sha256$"


def _password_material(password: str) -> bytes:
    # bcrypt truncates inputs beyond 72 bytes; pre-hashing prevents collisions.
    # codeql[py/weak-sensitive-data-hashing] bcrypt adds the per-hash salt and work factor after this bcrypt-sha256 prehash.
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


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
    """Hash password-reset and email-verification tokens before database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"
