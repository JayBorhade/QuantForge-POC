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
        owner_result = MagicMock()
        owner_result.scalar_one_or_none.return_value = type(
            "U", (), {"is_verified": True, "two_factor_enabled": True}
        )()
        db.execute.side_effect = [owner_result, query_result, MagicMock()]
        broker = AsyncMock()
        broker.submit_order.side_effect = BrokerSubmissionUnknown("network timeout after send")
        service = ExecutionService(db, broker)
        portfolio = type("P", (), {"id": "portfolio", "user_id": "user"})()

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

    def test_non_finite_quantity_and_prices_are_rejected_before_database_access(self):
        service = ExecutionService(AsyncMock())
        base = {
            "portfolio": type("P", (), {"id": "portfolio"})(),
            "symbol": "NIFTY",
            "side": OrderSide.BUY,
            "mode": ExecutionMode.PAPER,
            "client_order_id": "non-finite",
        }
        with self.assertRaisesRegex(ValueError, "quantity must be finite and positive"):
            asyncio.run(service.submit(quantity=Decimal("NaN"), **base))
        with self.assertRaisesRegex(ValueError, "estimated_price must be finite and positive"):
            asyncio.run(service.submit(
                quantity=Decimal("1"), estimated_price=Decimal("Infinity"), **base
            ))
        service.db.execute.assert_not_awaited()

    def test_live_requires_estimated_price_for_pre_trade_risk(self):
        db = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar_one_or_none.return_value = type(
            "U", (), {"is_verified": True, "two_factor_enabled": True}
        )()
        duplicate_result = MagicMock()
        duplicate_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [owner_result, duplicate_result]
        broker = AsyncMock()
        service = ExecutionService(db, broker)
        portfolio = type("P", (), {"id": "portfolio", "user_id": "user"})()

        with self.assertRaisesRegex(ValueError, "estimated price for pre-trade risk"):
            asyncio.run(service.submit(
                portfolio=portfolio,
                symbol="NIFTY",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                mode=ExecutionMode.LIVE,
                client_order_id="live-no-price",
            ))

        broker.submit_order.assert_not_awaited()

if __name__ == "__main__":

    unittest.main()
