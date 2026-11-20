"""Admin analytics must not fabricate operational metrics."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.api.routes.admin import get_analytics


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class AdminAnalyticsTests(unittest.TestCase):
    def test_analytics_uses_database_counts_and_marks_unavailable_metrics(self):
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            ScalarResult(12),
            ScalarResult(9),
            ScalarResult(4),
            ScalarResult(3),
        ])

        result = asyncio.run(get_analytics(MagicMock(), db))

        self.assertEqual(result["total_users"], 12)
        self.assertEqual(result["active_users"], 9)
        self.assertEqual(result["subscriptions"], 4)
        self.assertEqual(result["active_strategies"], 3)
        self.assertIsNone(result["api_requests_24h"])
        self.assertFalse(result["api_request_metrics_available"])
        self.assertEqual(result["server_status"], "database_connected")
        self.assertEqual(db.execute.await_count, 4)


if __name__ == "__main__":
    unittest.main()
