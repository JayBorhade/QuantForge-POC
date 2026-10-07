"""Execution service invariants."""

import unittest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.models.order import ExecutionMode, OrderSide, OrderType
from app.services.execution import ExecutionService


class ExecutionValidationTests(unittest.TestCase):
    def test_negative_quantity_rejected(self):
        service = ExecutionService(AsyncMock())
        import asyncio
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
        import asyncio
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


if __name__ == "__main__":
    unittest.main()
