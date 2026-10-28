"""Regression tests for risk-limit partial updates and event visibility."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
import uuid

from app.api.routes.risk import RiskLimitUpdate, update_risk_limits


class RiskLimitPatchSemanticsTests(unittest.TestCase):
    def test_omitted_kill_switch_is_not_an_implicit_disable(self):
        payload = RiskLimitUpdate(max_order_notional=Decimal("1000"))
        self.assertIsNone(payload.kill_switch)
        self.assertEqual(
            payload.model_dump(exclude_unset=True),
            {"max_order_notional": Decimal("1000")},
        )

    def test_explicit_kill_switch_false_is_preserved(self):
        payload = RiskLimitUpdate(kill_switch=False)
        self.assertEqual(payload.model_dump(exclude_unset=True), {"kill_switch": False})

    def test_explicit_null_can_clear_a_limit(self):
        payload = RiskLimitUpdate(max_daily_loss=None)
        self.assertEqual(payload.model_dump(exclude_unset=True), {"max_daily_loss": None})


if __name__ == "__main__":
    unittest.main()
