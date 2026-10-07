"""Unit tests for the deterministic paper broker."""

import asyncio
import unittest
from decimal import Decimal

from app.brokers.base import BrokerOrderRequest
from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.order import OrderSide, OrderType


def request(client_order_id: str = "client-1") -> BrokerOrderRequest:
    return BrokerOrderRequest(
        client_order_id=client_order_id,
        symbol="RELIANCE",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("2"),
    )


class PaperBrokerTests(unittest.TestCase):
    def test_submit_is_deterministic_and_idempotent(self):
        broker = PaperBrokerAdapter()
        first = asyncio.run(broker.submit_order(request()))
        second = asyncio.run(broker.submit_order(request()))
        self.assertEqual(first, second)
        self.assertEqual(first.broker_order_id, "paper-client-1")
        self.assertEqual(first.status, "submitted")

    def test_cancel_and_lookup(self):
        broker = PaperBrokerAdapter()
        submitted = asyncio.run(broker.submit_order(request()))
        asyncio.run(broker.cancel_order(submitted.broker_order_id))
        result = asyncio.run(broker.get_order(submitted.broker_order_id))
        self.assertEqual(result.status, "cancelled")

    def test_unknown_order_raises(self):
        broker = PaperBrokerAdapter()
        with self.assertRaises(KeyError):
            asyncio.run(broker.get_order("paper-missing"))

    def test_non_positive_quantity_rejected(self):
        broker = PaperBrokerAdapter()
        with self.assertRaises(ValueError):
            asyncio.run(
                broker.submit_order(
                    BrokerOrderRequest(
                        client_order_id="bad",
                        symbol="RELIANCE",
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=Decimal("0"),
                    )
                )
            )
