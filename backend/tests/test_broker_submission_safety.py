"""Broker adapters must preserve uncertain submissions and reconcile by client id."""

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.brokers.base import BrokerOrderRequest, BrokerSubmissionUnknown
from app.brokers.angel_one import AngelOneBrokerAdapter
from app.brokers.binance import BinanceBrokerAdapter
from app.brokers.zerodha import ZerodhaBrokerAdapter
from app.models.order import OrderSide, OrderType


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        return self.response


def request(broker_params=None):
    return BrokerOrderRequest(
        client_order_id="quantforge-client-order-123",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("1"),
        broker_params=broker_params or {},
    )


class BrokerSubmissionSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_zerodha_5xx_is_unknown_not_definitive_failure(self):
        adapter = ZerodhaBrokerAdapter("key", "secret", "access")
        response = SimpleNamespace(status_code=503)
        with patch("app.brokers.zerodha.httpx.AsyncClient", return_value=FakeClient(response)):
            with self.assertRaises(BrokerSubmissionUnknown):
                await adapter.submit_order(request({"exchange": "NSE", "product": "MIS"}))

    async def test_angel_one_5xx_is_unknown_not_definitive_failure(self):
        adapter = AngelOneBrokerAdapter("key", "secret", "access")
        response = SimpleNamespace(status_code=503)
        with patch("app.brokers.angel_one.httpx.AsyncClient", return_value=FakeClient(response)):
            with self.assertRaises(BrokerSubmissionUnknown):
                await adapter.submit_order(request({
                    "exchange": "NSE", "symboltoken": "123", "producttype": "INTRADAY"
                }))

    async def test_binance_5xx_is_unknown_not_definitive_failure(self):
        adapter = BinanceBrokerAdapter("key", "secret")
        response = SimpleNamespace(status_code=503)
        with patch("app.brokers.binance.httpx.AsyncClient", return_value=FakeClient(response)):
            with self.assertRaises(BrokerSubmissionUnknown):
                await adapter.submit_order(request())

    def test_client_tags_are_stable_and_within_provider_limits(self):
        client_id = "same-idempotency-key"
        self.assertEqual(
            ZerodhaBrokerAdapter._client_tag(client_id),
            ZerodhaBrokerAdapter._client_tag(client_id),
        )
        self.assertLessEqual(len(ZerodhaBrokerAdapter._client_tag(client_id)), 20)
        self.assertLess(len(AngelOneBrokerAdapter._client_tag(client_id)), 20)
        self.assertEqual(
            AngelOneBrokerAdapter._client_tag(client_id),
            AngelOneBrokerAdapter._client_tag(client_id),
        )


if __name__ == "__main__":
    unittest.main()
