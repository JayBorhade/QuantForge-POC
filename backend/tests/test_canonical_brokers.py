"""Deterministic tests for canonical broker adapters."""

import asyncio
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.brokers.angel_one import AngelOneBrokerAdapter
from app.brokers.base import BrokerOrderRequest
from app.brokers.binance import BinanceBrokerAdapter
from app.brokers.zerodha import ZerodhaBrokerAdapter
from app.models.order import OrderSide, OrderType


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.post = AsyncMock(return_value=response)
        self.get = AsyncMock(return_value=response)
        self.delete = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class CanonicalBrokerTests(unittest.TestCase):
    def request(self, **kwargs):
        return BrokerOrderRequest(
            client_order_id="client-123",
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("2"),
            limit_price=Decimal("2500"),
            **kwargs,
        )

    def test_zerodha_requires_exchange_and_product(self):
        broker = ZerodhaBrokerAdapter("key", "secret", "token")
        with self.assertRaises(ValueError):
            asyncio.run(broker.submit_order(self.request()))

    def test_zerodha_maps_successful_submission(self):
        broker = ZerodhaBrokerAdapter("key", "secret", "token")
        response = FakeResponse(200, {"status": "success", "data": {"order_id": "kite-1"}})
        client = FakeClient(response)
        with patch("app.brokers.zerodha.httpx.AsyncClient", return_value=client):
            result = asyncio.run(
                broker.submit_order(
                    self.request(broker_params={"exchange": "NSE", "product": "CNC"})
                )
            )
        self.assertEqual(result.broker_order_id, "kite-1")
        self.assertEqual(result.status, "submitted")
        payload = client.post.call_args.kwargs["data"]
        self.assertEqual(payload["transaction_type"], "BUY")
        self.assertEqual(payload["product"], "CNC")

    def test_zerodha_reconciles_cumulative_fill(self):
        broker = ZerodhaBrokerAdapter("key", "secret", "token")
        response = FakeResponse(
            200,
            {
                "status": "success",
                "data": [
                    {
                        "status": "COMPLETE",
                        "filled_quantity": 2,
                        "average_price": 2510,
                    }
                ],
            },
        )
        client = FakeClient(response)
        with patch("app.brokers.zerodha.httpx.AsyncClient", return_value=client):
            result = asyncio.run(broker.get_order("kite-1"))
        self.assertEqual(result.status, "filled")
        self.assertEqual(result.filled_quantity, Decimal("2"))
        self.assertEqual(result.average_fill_price, Decimal("2510"))

    def test_binance_preserves_symbol_in_broker_order_id(self):
        broker = BinanceBrokerAdapter("key", "secret")
        response = FakeResponse(200, {"orderId": 42, "status": "NEW"})
        client = FakeClient(response)
        with patch("app.brokers.binance.httpx.AsyncClient", return_value=client):
            result = asyncio.run(broker.submit_order(self.request()))
        self.assertEqual(result.broker_order_id, "binance:RELIANCE:42")
        self.assertEqual(result.status, "submitted")
        params = client.post.call_args.kwargs["params"]
        self.assertEqual(params["newClientOrderId"], "client-123")
        self.assertIn("signature", params)

    def test_binance_order_id_round_trips_for_cancel(self):
        broker = BinanceBrokerAdapter("key", "secret")
        response = FakeResponse(200, {"orderId": 42, "status": "CANCELED"})
        client = FakeClient(response)
        with patch("app.brokers.binance.httpx.AsyncClient", return_value=client):
            asyncio.run(broker.cancel_order("binance:BTCUSDT:42"))
        params = client.delete.call_args.kwargs["params"]
        self.assertEqual(params["symbol"], "BTCUSDT")
        self.assertEqual(params["orderId"], "42")

    def test_angel_one_reconciles_cumulative_fill(self):
        broker = AngelOneBrokerAdapter("key", "secret", "token")
        response = FakeResponse(
            200,
            {
                "status": True,
                "data": {
                    "orderstatus": "complete",
                    "filledshares": "3",
                    "averageprice": "2512.50",
                },
            },
        )
        client = FakeClient(response)
        with patch("app.brokers.angel_one.httpx.AsyncClient", return_value=client):
            result = asyncio.run(broker.get_order("angel-1"))
        self.assertEqual(result.status, "filled")
        self.assertEqual(result.filled_quantity, Decimal("3"))
        self.assertEqual(result.average_fill_price, Decimal("2512.50"))

    def test_angel_one_requires_instrument_metadata(self):
        broker = AngelOneBrokerAdapter("key", "secret", "token")
        with self.assertRaises(ValueError):
            asyncio.run(broker.submit_order(self.request()))

    def test_angel_one_maps_submission(self):
        broker = AngelOneBrokerAdapter("key", "secret", "token")
        response = FakeResponse(200, {"status": True, "data": {"orderid": "angel-1"}})
        client = FakeClient(response)
        with patch("app.brokers.angel_one.httpx.AsyncClient", return_value=client):
            result = asyncio.run(
                broker.submit_order(
                    self.request(
                        broker_params={
                            "exchange": "NSE",
                            "symboltoken": "3045",
                            "producttype": "DELIVERY",
                        }
                    )
                )
            )
        self.assertEqual(result.broker_order_id, "angel-1")
        self.assertEqual(result.status, "submitted")


if __name__ == "__main__":
    unittest.main()
