"""Tests for automated broker reconciliation tasks."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.order import ExecutionMode, OrderStatus
from app.tasks.reconciliation_tasks import reconcile_broker_order, reconcile_broker_orders


class ReconciliationTaskTests(unittest.TestCase):
    def _session(self, db):
        return MagicMock(
            __aenter__=AsyncMock(return_value=db),
            __aexit__=AsyncMock(return_value=False),
        )

    def test_sweep_reconciles_and_isolates_order_failures(self):
        first_id, second_id = uuid4(), uuid4()
        db = MagicMock()
        db.bind.dialect.name = "sqlite"
        db.execute = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[(first_id,), (second_id,)]))
        )
        db.commit = AsyncMock()

        with patch("app.tasks.reconciliation_tasks.AsyncSessionLocal", return_value=self._session(db)),              patch(
                 "app.tasks.reconciliation_tasks._reconcile_order",
                 new=AsyncMock(side_effect=[
                     {"order_id": str(first_id), "status": "filled", "filled_quantity": "1"},
                     RuntimeError("broker timeout"),
                 ]),
             ) as reconcile:
            result = reconcile_broker_orders.run()

        self.assertEqual(result["reconciled"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(reconcile.await_count, 2)
        db.commit.assert_awaited_once()

    def test_sweep_counts_unresolved_submission(self):
        order_id = uuid4()
        db = MagicMock()
        db.bind.dialect.name = "sqlite"
        db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(order_id,)])))
        db.commit = AsyncMock()

        with patch("app.tasks.reconciliation_tasks.AsyncSessionLocal", return_value=self._session(db)),              patch(
                 "app.tasks.reconciliation_tasks._reconcile_order",
                 new=AsyncMock(return_value={"order_id": str(order_id), "status": "unresolved"}),
             ):
            result = asyncio.run(reconcile_broker_orders.run())

        self.assertEqual(result["unresolved"], 1)
        self.assertEqual(result["failed"], 0)

    def test_targeted_task_skips_non_live_order(self):
        order = MagicMock(mode=ExecutionMode.PAPER, status=OrderStatus.SUBMITTED)
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: order))

        with patch("app.tasks.reconciliation_tasks.AsyncSessionLocal", return_value=self._session(db)):
            result = reconcile_broker_order.run(str(uuid4()))

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "not_live")
        db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
