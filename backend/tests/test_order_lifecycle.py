"""Tests for order lifecycle transitions and reconciliation."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.brokers.base import BrokerOrderResult
from app.models.order import OrderStatus
from decimal import Decimal
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

        self.assertIs(result, locked)
        self.assertEqual(locked.status, OrderStatus.CANCELLED)
        broker.cancel_order.assert_awaited_once_with("paper-1")
        self.assertGreaterEqual(db.flush.await_count, 1)

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
        locked = MagicMock(status=OrderStatus.SUBMITTED, broker_order_id="paper-1", filled_quantity=0, quantity=2)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        broker.get_order = AsyncMock(
            return_value=BrokerOrderResult("paper-1", "partially_filled")
        )
        order = MagicMock(id="order-1")

        result = asyncio.run(OrderLifecycleService(db, broker).reconcile(order))

        self.assertIs(result, locked)
        self.assertEqual(locked.status, OrderStatus.PARTIALLY_FILLED)
        self.assertGreaterEqual(db.flush.await_count, 1)

    def test_reconcile_open_orders_processes_only_open_orders(self):
        db = MagicMock()
        db.flush = AsyncMock()
        open_order = MagicMock(
            id="open-1",
            status=OrderStatus.SUBMITTED,
            broker_order_id="paper-open",
            filled_quantity=0,
            quantity=2,
        )
        result = MagicMock()
        result.scalars.return_value.all.return_value = [open_order]
        db.execute = AsyncMock(side_effect=[
            result,
            MagicMock(scalar_one_or_none=lambda: open_order),
        ])
        broker = MagicMock()
        broker.get_order = AsyncMock(
            return_value=BrokerOrderResult("paper-open", "submitted")
        )

        orders = asyncio.run(OrderLifecycleService(db, broker).reconcile_open_orders())

        self.assertEqual(orders, [open_order])
        self.assertEqual(open_order.status, OrderStatus.SUBMITTED)
        broker.get_order.assert_awaited_once_with("paper-open")

    def test_reconcile_audits_status_change(self):
        db = MagicMock()
        db.flush = AsyncMock()
        locked = MagicMock(
            id="order-1",
            status=OrderStatus.SUBMITTED,
            broker_order_id="paper-1",
            filled_quantity=0,
            quantity=2,
        )
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        broker.get_order = AsyncMock(
            return_value=BrokerOrderResult("paper-1", "partially_filled")
        )
        order = MagicMock(id="order-1")

        with patch("app.services.order_lifecycle.log_audit", new_callable=AsyncMock) as audit:
            result = asyncio.run(OrderLifecycleService(db, broker).reconcile(order))

        self.assertIs(result, locked)
        audit.assert_awaited_once()
        self.assertEqual(audit.await_args.kwargs["action"], "order.reconciled")
        self.assertEqual(audit.await_args.kwargs["details"]["previous_status"], "submitted")
        self.assertEqual(audit.await_args.kwargs["details"]["new_status"], "partially_filled")

    def test_reconcile_ingests_new_cumulative_fill(self):
        db = MagicMock()
        db.flush = AsyncMock()
        locked = MagicMock(
            id="order-1", status=OrderStatus.SUBMITTED, broker_order_id="broker-1",
            filled_quantity=Decimal("2"), quantity=Decimal("4"),
            average_fill_price=Decimal("100"),
        )
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        broker.get_order = AsyncMock(return_value=BrokerOrderResult(
            "broker-1", "filled", filled_quantity=Decimal("4"), average_fill_price=Decimal("105")
        ))
        fill = MagicMock()
        with patch("app.services.order_lifecycle.FillService.apply_fill", new=AsyncMock(return_value=fill)) as apply:
            result = asyncio.run(OrderLifecycleService(db, broker).reconcile(locked))

        self.assertIs(result, locked)
        apply.assert_awaited_once()
        kwargs = apply.await_args.kwargs
        self.assertEqual(kwargs["quantity"], Decimal("2"))
        self.assertEqual(kwargs["price"], Decimal("110"))
        self.assertEqual(kwargs["broker_fill_id"], "broker:broker-1:filled:4")

    def test_reconcile_does_not_regress_filled_order(self):
        db = MagicMock()
        locked = MagicMock(status=OrderStatus.FILLED, broker_order_id="paper-1", filled_quantity=2, quantity=2)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: locked))
        broker = MagicMock()
        broker.get_order = AsyncMock(return_value=BrokerOrderResult("paper-1", "cancelled"))
        order = MagicMock(id="order-1")

        with self.assertRaises(ValueError):
            asyncio.run(OrderLifecycleService(db, broker).reconcile(order))


if __name__ == "__main__":
    unittest.main()
