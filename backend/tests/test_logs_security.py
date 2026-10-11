"""Regression tests for safe logs and live health probes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from app.api.routes.logs import _probe_database, strategy_logs


class LogsSecurityTests(IsolatedAsyncioTestCase):
    async def test_strategy_error_details_are_not_returned_to_users(self):
        user_id = "user-1"
        run = SimpleNamespace(
            id="run-1",
            started_at=None,
            created_at=datetime.now(timezone.utc),
            error_message="provider failed: api_secret=super-secret-value",
            status=SimpleNamespace(value="failed"),
            mode=SimpleNamespace(value="paper"),
            sharpe_ratio=None,
            total_return=None,
        )
        result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [run]))
        db = SimpleNamespace(execute=AsyncMock(return_value=result))

        logs = await strategy_logs(SimpleNamespace(id=user_id), db, limit=10)

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["level"], "ERROR")
        self.assertNotIn("super-secret-value", logs[0]["message"])
        self.assertNotIn("api_secret", logs[0]["message"])
        self.assertIn("run ID", logs[0]["message"])

    async def test_database_probe_reports_success_only_after_query_succeeds(self):
        result = SimpleNamespace(scalar_one=lambda: 1)
        db = SimpleNamespace(execute=AsyncMock(return_value=result))

        self.assertEqual(await _probe_database(db), "healthy")
        db.execute.assert_awaited_once()

    async def test_database_probe_fails_closed_when_query_raises(self):
        db = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("private connection details")))

        self.assertEqual(await _probe_database(db), "unavailable")


if __name__ == "__main__":
    import unittest

    unittest.main()
