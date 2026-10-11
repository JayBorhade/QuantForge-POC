"""Shared API rate limiter; Redis backs distributed deployments."""
import hashlib

from fastapi import HTTPException
from redis.asyncio import Redis
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


async def enforce_account_rate_limit(
    identifier: str,
    action: str,
    *,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """Apply a distributed per-account fixed-window limit using Redis.

    Local/test environments rely on the ordinary IP limiter. In deployed
    environments, Redis errors fail closed so account-scoped limits cannot
    silently disappear during an outage.
    """
    if settings.app_env.strip().lower() in _local_envs:
        return
    digest = hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()
    key = f"quantforge:account-limit:{action}:{digest}"
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        # A Lua script makes increment + first-hit expiry atomic across replicas.
        count = int(await client.eval(
            "local n = redis.call('INCR', KEYS[1]); "
            "if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
            "return n",
            1,
            key,
            window_seconds,
        ))
        if count > limit:
            ttl = await client.ttl(key)
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(max(1, ttl))},
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable.",
        )
    finally:
        await client.aclose()
