"""Canonical Zerodha Kite Connect execution adapter."""

from __future__ import annotations

from decimal import Decimal
import hashlib
from typing import Any, Mapping

import httpx

from app.brokers.base import BrokerOrderRequest, BrokerOrderResult, BrokerSubmissionUnknown, BrokerSubmissionRejected
from app.models.order import OrderSide, OrderType


class ZerodhaBrokerAdapter:
    BASE_URL = "https://api.kite.trade"
    _TIMEOUT = httpx.Timeout(10.0)

    def __init__(self, api_key: str, api_secret: str, access_token: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.access_token:
            raise ValueError("Zerodha requires api_key and access_token")
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
        }

    @staticmethod
    def _status(value: str) -> str:
        status = value.strip().upper()
        if status in {"COMPLETE", "FILLED"}:
            return "filled"
        if status in {"CANCELLED", "CANCELED"}:
            return "cancelled"
        if status in {"REJECTED"}:
            return "rejected"
        if status in {
            "OPEN", "OPEN PENDING", "VALIDATION PENDING",
            "PUT ORDER REQ RECEIVED", "AMO REQ RECEIVED",
            "TRIGGER PENDING", "MODIFY PENDING", "CANCEL PENDING",
            "PARTIALLY FILLED",
        }:
            if status == "PARTIALLY FILLED":
                return "partially_filled"
            return "submitted"
        raise ValueError("Unsupported Zerodha order status")
    
    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(f"{self.BASE_URL}/user/profile", headers=self._headers())
                response.raise_for_status()
                return response.json().get("status") == "success"
        except (httpx.HTTPError, ValueError):
            return False

    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        params = dict(request.broker_params)
        exchange = params.get("exchange")
        product = params.get("product")
        if not exchange or not product:
            raise ValueError("Zerodha order requires broker_params.exchange and broker_params.product")

        payload: dict[str, Any] = {
            "tradingsymbol": request.symbol,
            "exchange": exchange,
            "transaction_type": request.side.value.upper(),
            "order_type": request.order_type.value.upper(),
            "quantity": str(request.quantity),
            "product": product,
            "validity": params.get("validity", "DAY"),
        }
        if request.order_type is OrderType.LIMIT:
            if request.limit_price is None:
                raise ValueError("Zerodha LIMIT order requires limit_price")
            payload["price"] = str(request.limit_price)
        if params.get("market_protection") is not None:
            payload["market_protection"] = params["market_protection"]
        # Kite tags are visible in the order book. Use a stable, compact
        # digest of our idempotency key so an ambiguous submission can be
        # reconciled without blindly resubmitting it.
        payload["tag"] = "qf" + hashlib.sha256(request.client_order_id.encode()).hexdigest()[:18]
        if params.get("autoslice") is not None:
            payload["autoslice"] = params["autoslice"]

        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/orders/regular",
                headers=self._headers(),
                data=payload,
            )
            if response.status_code >= 500:
                raise BrokerSubmissionUnknown(
                    f"Zerodha returned HTTP {response.status_code}; order outcome is unknown"
                )
            data = response.json()
            if response.status_code >= 400 or data.get("status") != "success":
                raise BrokerSubmissionRejected(
                    data.get("message") or f"Zerodha rejected the order ({response.status_code})"
                )
            return BrokerOrderResult(str(data["data"]["order_id"]), "submitted")

    @staticmethod
    def _client_tag(client_order_id: str) -> str:
        return "qf" + hashlib.sha256(client_order_id.encode()).hexdigest()[:18]

    async def find_order_by_client_order_id(
        self, client_order_id: str, symbol: str
    ) -> BrokerOrderResult | None:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(f"{self.BASE_URL}/orders", headers=self._headers())
            if response.status_code >= 500:
                raise BrokerSubmissionUnknown(
                    f"Zerodha order-book lookup returned HTTP {response.status_code}"
                )
            response.raise_for_status()
            data = response.json()
        if data.get("status") != "success":
            raise RuntimeError("Zerodha order-book lookup failed")
        expected_tag = self._client_tag(client_order_id)
        for item in data.get("data") or []:
            if item.get("tag") != expected_tag:
                continue
            if str(item.get("tradingsymbol", "")).upper() != symbol.upper():
                continue
            filled = Decimal(str(item.get("filled_quantity", "0")))
            average = Decimal(str(item.get("average_price", "0")))
            return BrokerOrderResult(
                broker_order_id=str(item["order_id"]),
                status=self._status(str(item.get("status", "OPEN"))),
                filled_quantity=filled,
                average_fill_price=average if average > 0 else None,
            )
        return None

    async def cancel_order(self, broker_order_id: str) -> None:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.delete(
                f"{self.BASE_URL}/orders/regular/{broker_order_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                raise RuntimeError(data.get("message") or "Zerodha cancellation failed")

    async def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/orders/{broker_order_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success" or not data.get("data"):
                raise RuntimeError(data.get("message") or "Zerodha order lookup failed")
            latest: Mapping[str, Any] = data["data"][-1]
            filled_quantity = Decimal(str(latest.get("filled_quantity", "0")))
            average_fill_price_raw = latest.get("average_price")
            average_fill_price = (
                Decimal(str(average_fill_price_raw))
                if average_fill_price_raw not in (None, "", 0, "0")
                else None
            )
            return BrokerOrderResult(
                broker_order_id=broker_order_id,
                status=self._status(str(latest.get("status", ""))),
                filled_quantity=filled_quantity,
                average_fill_price=average_fill_price,
            )

    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/quote/ltp",
                headers=self._headers(),
                params={"i": f"{exchange}:{symbol}"},
            )
            response.raise_for_status()
            data = response.json()
            quote = data.get("data", {}).get(f"{exchange}:{symbol}", {})
            return {"symbol": symbol, "price": quote.get("last_price"), "broker": "zerodha"}

    async def get_positions(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(f"{self.BASE_URL}/portfolio/positions", headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("net", [])
