"""Canonical Angel One SmartAPI execution adapter."""

from __future__ import annotations

from decimal import Decimal
import hashlib
from typing import Any

import httpx

from app.brokers.base import BrokerOrderRequest, BrokerOrderResult, BrokerSubmissionUnknown, BrokerSubmissionRejected
from app.models.order import OrderType


class AngelOneBrokerAdapter:
    BASE_URL = "https://apiconnect.angelone.in"
    _TIMEOUT = httpx.Timeout(10.0)

    def __init__(self, api_key: str, api_secret: str, access_token: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.access_token:
            raise ValueError("Angel One requires api_key and access_token")
        return {
            "X-PrivateKey": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
        }

    @staticmethod
    def _status(value: str) -> str:
        value = value.strip().upper()
        if value in {"COMPLETE", "FILLED"}:
            return "filled"
        if value in {"CANCELLED", "CANCELED"}:
            return "cancelled"
        if value in {"REJECTED"}:
            return "rejected"
        if value in {"OPEN", "PENDING", "TRIGGER PENDING", "OPEN PENDING"}:
            return "submitted"
        if "PART" in value:
            return "partially_filled"
        raise ValueError("Unsupported Angel One order status")

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/rest/secure/angelbroking/user/v1/getProfile",
                    headers=self._headers(),
                )
                return response.status_code == 200 and response.json().get("status") is True
        except (httpx.HTTPError, ValueError):
            return False

    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        required = ("exchange", "symboltoken", "producttype")
        missing = [key for key in required if not request.broker_params.get(key)]
        if missing:
            raise BrokerSubmissionRejected(f"Angel One order missing broker_params: {', '.join(missing)}")

        # Angel One exposes ordertag in its order book; derive a deterministic
        # compact tag from the client id so uncertain submissions can be found.
        client_tag = "qf" + hashlib.sha256(request.client_order_id.encode()).hexdigest()[:17]
        payload: dict[str, Any] = {
            "variety": request.broker_params.get("variety", "NORMAL"),
            "tradingsymbol": request.symbol,
            "symboltoken": request.broker_params["symboltoken"],
            "transactiontype": request.side.value.upper(),
            "exchange": request.broker_params["exchange"],
            "ordertype": request.order_type.value.upper(),
            "producttype": request.broker_params["producttype"],
            "duration": request.broker_params.get("duration", "DAY"),
            "quantity": str(request.quantity),
            "price": str(request.limit_price or 0),
            "squareoff": "0",
            "stoploss": "0",
            "ordertag": client_tag,
        }
        if request.order_type is OrderType.LIMIT and request.limit_price is None:
            raise BrokerSubmissionRejected("Angel One LIMIT order requires limit_price")

        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/placeOrder",
                headers=self._headers(),
                json=payload,
            )
            if response.status_code >= 500:
                raise BrokerSubmissionUnknown(
                    f"Angel One returned HTTP {response.status_code}; order outcome is unknown"
                )
            data = response.json()
            if response.status_code >= 400 or data.get("status") is not True:
                raise BrokerSubmissionRejected(
                    data.get("message") or f"Angel One rejected the order ({response.status_code})"
                )
            order_id = (data.get("data") or {}).get("orderid") or (data.get("data") or {}).get("uniqueorderid")
            unique_order_id = (data.get("data") or {}).get("uniqueorderid")
            if not order_id or not unique_order_id:
                raise BrokerSubmissionUnknown(
                    "Angel One may have accepted the order without returning complete order identifiers"
                )
            return BrokerOrderResult(
                f"angelone:{order_id}:{unique_order_id}", "submitted"
            )

    @staticmethod
    def _client_tag(client_order_id: str) -> str:
        return "qf" + hashlib.sha256(client_order_id.encode()).hexdigest()[:17]

    async def find_order_by_client_order_id(
        self, client_order_id: str, symbol: str
    ) -> BrokerOrderResult | None:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getOrderBook",
                headers=self._headers(),
            )
            if response.status_code >= 500:
                raise BrokerSubmissionUnknown(
                    f"Angel One order-book lookup returned HTTP {response.status_code}"
                )
            response.raise_for_status()
            data = response.json()
        if data.get("status") is not True:
            raise RuntimeError("Angel One order-book lookup failed")
        expected_tag = self._client_tag(client_order_id)
        for item in data.get("data") or []:
            tag = item.get("ordertag") or item.get("orderTag")
            if tag != expected_tag:
                continue
            if str(item.get("tradingsymbol", "")).upper() != symbol.upper():
                continue
            filled = Decimal(str(item.get("filledshares", "0")))
            average = Decimal(str(item.get("averageprice", "0")))
            order_id = item.get("orderid")
            unique_order_id = item.get("uniqueorderid")
            if not order_id or not unique_order_id:
                raise BrokerSubmissionUnknown("Angel One order book returned incomplete order identifiers")
            return BrokerOrderResult(
                broker_order_id=f"angelone:{order_id}:{unique_order_id}",
                status=self._status(str(item.get("orderstatus") or item.get("status", "open"))),
                filled_quantity=filled,
                average_fill_price=average if average > 0 else None,
            )
        return None

    @staticmethod
    def _split_broker_order_id(broker_order_id: str) -> tuple[str, str]:
        if broker_order_id.startswith("angelone:"):
            parts = broker_order_id.split(":", 2)
            if len(parts) == 3 and parts[1] and parts[2]:
                return parts[1], parts[2]
            raise ValueError("Invalid Angel One broker order identifier")
        # Backward compatibility for orders created before composite IDs.
        return broker_order_id, broker_order_id

    async def cancel_order(self, broker_order_id: str) -> None:
        order_id, _ = self._split_broker_order_id(broker_order_id)
        payload = {"variety": "NORMAL", "orderid": order_id}
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/cancelOrder",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") is not True:
                raise RuntimeError(data.get("message") or "Angel One cancellation failed")

    async def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        _, unique_order_id = self._split_broker_order_id(broker_order_id)
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/details/{unique_order_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") is not True:
                raise RuntimeError(data.get("message") or "Angel One order lookup failed")
            details = data.get("data") or {}
            filled_quantity_raw = next(
                (details.get(key) for key in ("filledshares", "filledquantity", "filled_quantity") if details.get(key) not in (None, "")),
                "0",
            )
            filled_quantity = Decimal(str(filled_quantity_raw))
            average_fill_price_raw = next(
                (details.get(key) for key in ("averageprice", "average_price") if details.get(key) not in (None, "")),
                None,
            )
            average_fill_price = (
                Decimal(str(average_fill_price_raw))
                if average_fill_price_raw not in (None, "", 0, "0")
                else None
            )
            return BrokerOrderResult(
                broker_order_id=broker_order_id,
                status=self._status(str(details.get("orderstatus", details.get("status", "")))),
                filled_quantity=filled_quantity,
                average_fill_price=average_fill_price,
            )

    async def get_quote(self, symbol: str, exchange: str, symboltoken: str) -> dict[str, Any]:
        payload = {"exchange": exchange, "tradingsymbol": symbol, "symboltoken": symboltoken}
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/rest/secure/angelbroking/market/v1/quote/",
                headers=self._headers(),
                json={"mode": "LTP", "exchangeTokens": {exchange: [symboltoken]}},
            )
            response.raise_for_status()
            data = response.json()
            fetched = (data.get("data") or {}).get("fetched") or []
            return {"symbol": symbol, "price": fetched[0].get("ltp") if fetched else None, "broker": "angel_one", **payload}

    async def get_positions(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getPosition",
                headers=self._headers(),
            )
            response.raise_for_status()
            return (response.json().get("data") or [])
