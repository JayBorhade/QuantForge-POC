"""Tests for distributed per-account authentication throttling."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core.rate_limit import enforce_account_rate_limit


class FakePipeline:
    def __init__(self, results=None, error=None):
        self.results = results or [1, True]
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def incr(self, key):
        return self

    def expire(self, key, seconds, nx=False):
        return self

    async def execute(self):
        if self.error:
            raise self.error
        return self.results


class AccountRateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_environment_does_not_require_redis(self):
        with patch("app.core.rate_limit.settings", SimpleNamespace(app_env="test", redis_url="redis://invalid")):
            with patch("app.core.rate_limit.Redis.from_url") as from_url:
                await enforce_account_rate_limit("user@example.com", "login", limit=2)
        from_url.assert_not_called()

    async def test_distributed_limit_returns_429_after_limit(self):
        client = AsyncMock()
        client.pipeline.return_value = FakePipeline([3, True])
        client.ttl.return_value = 30
        with patch("app.core.rate_limit.settings", SimpleNamespace(app_env="production", redis_url="redis://redis")), patch(
            "app.core.rate_limit.Redis.from_url", return_value=client
        ):
            with self.assertRaises(HTTPException) as raised:
                await enforce_account_rate_limit("user@example.com", "login", limit=2)
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "30")
        client.aclose.assert_awaited_once()

    async def test_redis_outage_fails_closed(self):
        client = AsyncMock()
        client.pipeline.return_value = FakePipeline(error=RuntimeError("redis down"))
        with patch("app.core.rate_limit.settings", SimpleNamespace(app_env="production", redis_url="redis://redis")), patch(
            "app.core.rate_limit.Redis.from_url", return_value=client
        ):
            with self.assertRaises(HTTPException) as raised:
                await enforce_account_rate_limit("user@example.com", "login", limit=2)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("redis down", raised.exception.detail)
        client.aclose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
