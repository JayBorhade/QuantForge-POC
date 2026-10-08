"""Execution service invariants."""

import asyncio
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.brokers.base import BrokerSubmissionUnknown
from app.models.order import ExecutionMode, OrderSide, OrderStatus, OrderType
from app.services.execution import ExecutionService


class ExecutionValidationTests(unittest.TestCase):
    def test_negative_quantity_rejected(self):
        service = ExecutionService(AsyncMock())
        with self.assertRaises(ValueError):
            asyncio.run(service.submit(
                portfolio=type("P", (), {"id": "portfolio"})(),
                symbol="NIFTY",
                side=OrderSide.BUY,
                quantity=Decimal("-1"),
                mode=ExecutionMode.PAPER,
                client_order_id="test-1",
            ))

    def test_live_requires_broker(self):
        service = ExecutionService(AsyncMock())
        with self.assertRaises(ValueError):
            asyncio.run(service.submit(
                portfolio=type("P", (), {"id": "portfolio"})(),
                symbol="NIFTY",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                mode=ExecutionMode.LIVE,
                client_order_id="test-2",
                order_type=OrderType.MARKET,
            ))

    def test_uncertain_submission_is_not_marked_failed(self):
        db = AsyncMock()
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        db.execute.return_value = query_result
        broker = AsyncMock()
        broker.submit_order.side_effect = BrokerSubmissionUnknown("network timeout after send")
        service = ExecutionService(db, broker)
        portfolio = type("P", (), {"id": "portfolio"})()

        with patch("app.services.execution.RiskService.require_approval", new=AsyncMock()):
            with self.assertRaises(BrokerSubmissionUnknown):
                asyncio.run(service.submit(
                    portfolio=portfolio,
                    symbol="NIFTY",
                    side=OrderSide.BUY,
                    quantity=Decimal("1"),
                    mode=ExecutionMode.LIVE,
                    client_order_id="test-unknown",
                ))

        created_order = next(call.args[0] for call in db.add.call_args_list if call.args)
        self.assertEqual(created_order.status, OrderStatus.SUBMISSION_UNKNOWN)
        self.assertNotEqual(created_order.status, OrderStatus.FAILED)
        broker.submit_order.assert_awaited_once()

    def test_live_requires_verified_two_factor_owner(self):
        db = AsyncMock()
        duplicate = MagicMock()
        duplicate.scalar_one_or_none.return_value = None
        owner_result = MagicMock()
        owner_result.scalar_one_or_none.return_value = type(
            "U", (), {"is_verified": False, "two_factor_enabled": False}
        )()
        db.execute.side_effect = [duplicate, owner_result]
        broker = AsyncMock()
        service = ExecutionService(db, broker)
        portfolio = type("P", (), {"id": "portfolio", "user_id": "user"})()

        with self.assertRaisesRegex(ValueError, "verified account"):
            asyncio.run(service.submit(
                portfolio=portfolio,
                symbol="NIFTY",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                mode=ExecutionMode.LIVE,
                client_order_id="test-unverified",
            ))

        broker.submit_order.assert_not_awaited()

if __name__ == "__main__":

    unittest.main()
