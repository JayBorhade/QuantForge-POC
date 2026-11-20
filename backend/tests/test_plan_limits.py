"""Plan limits default closed and remain finite for every tier."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.subscription import PlanTier, SubscriptionStatus
from app.services.plan_limits import PLAN_LIMITS, get_effective_limits


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class PlanLimitTests(unittest.TestCase):
    def test_missing_subscription_gets_free_limits(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=ScalarResult(None))
        limits = asyncio.run(get_effective_limits(db, "user-id"))
        self.assertEqual(limits, PLAN_LIMITS[PlanTier.FREE])

    def test_inactive_paid_subscription_does_not_keep_paid_limits(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=ScalarResult(SimpleNamespace(
            plan=PlanTier.PRO, status=SubscriptionStatus.EXPIRED
        )))
        limits = asyncio.run(get_effective_limits(db, "user-id"))
        self.assertEqual(limits, PLAN_LIMITS[PlanTier.FREE])

    def test_active_paid_subscription_gets_finite_limits(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=ScalarResult(SimpleNamespace(
            plan=PlanTier.PRO, status=SubscriptionStatus.ACTIVE
        )))
        limits = asyncio.run(get_effective_limits(db, "user-id"))
        self.assertEqual(limits, PLAN_LIMITS[PlanTier.PRO])
        self.assertTrue(limits.strategies < 10**9)
        self.assertTrue(limits.portfolios < 10**9)


if __name__ == "__main__":
    unittest.main()
