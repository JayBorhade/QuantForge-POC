"""Shared API rate limiter; Redis backs distributed deployments."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()
_local_envs = {"development", "local", "test"}
_storage_uri = "memory://" if settings.app_env.strip().lower() in _local_envs else settings.redis_url

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri=_storage_uri,
    headers_enabled=False,
)
