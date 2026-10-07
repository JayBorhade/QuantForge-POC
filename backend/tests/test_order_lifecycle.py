"""Tests for order lifecycle transitions and reconciliation."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.brokers.base import BrokerOrderResult
from app.models.order import OrderStatus
from app.services.order_lifecycle import OrderLifecycleService, OrderStatusMapper


class OrderLifecycleTests(unittest.TestCase):
    def test_maps_provider_statuses(self):
        self.assertEqual(OrderStatusMapper.from_broker_status("accepted"), OrderStatus.SUBMITTED)
        self.assertEqual(OrderStatusMapper.from_broker_status("partial"), OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(OrderStatusMapper.from_broker_status("canceled"), OrderStatus.CANCELLED)
        self.assertEqual(OrderStatusMapper.from_broker_status("rejected"), OrderStatus.REJECTED)

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            OrderStatusMapper.from_broker_status("mystery")

    def test_cancel_calls_broker_and_updates_order(self):
        db = MagicMock()
        db.flush = AsyncMock()
        locked = MagicMock(status=OrderStatus.SUBMITTED, broker_order_id="paper-1")
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        broker.cancel_order = AsyncMock()
        order = MagicMock(id="order-1")

        result = asyncio.run(OrderLifecycleService(db, broker).cancel(order))

        self.assertIs(result, order)
        self.assertEqual(locked.status, OrderStatus.CANCELLED)
        broker.cancel_order.assert_awaited_once_with("paper-1")
        db.flush.assert_awaited_once()

    def test_terminal_order_cannot_be_cancelled(self):
        db = MagicMock()
        locked = MagicMock(status=OrderStatus.FILLED, broker_order_id="paper-1")
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        order = MagicMock(id="order-1")

        with self.assertRaises(ValueError):
            asyncio.run(OrderLifecycleService(db, broker).cancel(order))

        broker.cancel_order.assert_not_called()

    def test_reconcile_updates_status(self):
        db = MagicMock()
        db.flush = AsyncMock()
        broker = MagicMock()
        broker.get_order = AsyncMock(
            return_value=BrokerOrderResult("paper-1", "partially_filled")
        )
        order = MagicMock(status=OrderStatus.SUBMITTED, broker_order_id="paper-1")

        result = asyncio.run(OrderLifecycleService(db, broker).reconcile(order))

        self.assertIs(result, order)
        self.assertEqual(order.status, OrderStatus.PARTIALLY_FILLED)
        db.flush.assert_awaited_once()

    def test_reconcile_does_not_regress_filled_order(self):
        db = MagicMock()
        broker = MagicMock()
        broker.get_order = AsyncMock(return_value=BrokerOrderResult("paper-1", "cancelled"))
        order = MagicMock(status=OrderStatus.FILLED, broker_order_id="paper-1")

        with self.assertRaises(ValueError):
            asyncio.run(OrderLifecycleService(db, broker).reconcile(order))


if __name__ == "__main__":
    unittest.main()
