"""Tests for conservative stale-order reconciliation."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models.order import OrderStatus
from app.services.reconciliation import ReconciliationService


class ReconciliationTests(unittest.TestCase):
    def test_invalid_age_is_rejected(self):
        with self.assertRaises(ValueError):
            asyncio.run(ReconciliationService(MagicMock(), MagicMock()).reconcile_stale_orders(0))

    def test_stale_open_orders_are_reconciled(self):
        db = MagicMock()
        db.execute = AsyncMock()
        order = MagicMock(
            status=OrderStatus.SUBMITTED,
            broker_order_id="paper-1",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        result = MagicMock()
        result.scalars.return_value.all.return_value = [order]
        db.execute.return_value = result

        lifecycle = MagicMock()
        lifecycle.reconcile = AsyncMock(return_value=order)
        service = ReconciliationService(db, MagicMock())
        service.lifecycle = lifecycle

        orders = asyncio.run(service.reconcile_stale_orders(300))

        self.assertEqual(orders, [order])
        lifecycle.reconcile.assert_awaited_once_with(order)


if __name__ == "__main__":
    unittest.main()
