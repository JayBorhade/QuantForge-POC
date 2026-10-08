"""Canonical Angel One SmartAPI execution adapter."""

from __future__ import annotations

from typing import Any

import httpx

from app.brokers.base import BrokerOrderRequest, BrokerOrderResult
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
        return "failed"

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
            raise ValueError(f"Angel One order missing broker_params: {', '.join(missing)}")

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
        }
        if request.order_type is OrderType.LIMIT and request.limit_price is None:
            raise ValueError("Angel One LIMIT order requires limit_price")

        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/placeOrder",
                headers=self._headers(),
                json=payload,
            )
            data = response.json()
            if response.status_code >= 400 or data.get("status") is not True:
                raise RuntimeError(data.get("message") or "Angel One order failed")
            order_id = (data.get("data") or {}).get("orderid") or (data.get("data") or {}).get("uniqueorderid")
            if not order_id:
                raise RuntimeError("Angel One did not return an order id")
            return BrokerOrderResult(str(order_id), "submitted")

    async def cancel_order(self, broker_order_id: str) -> None:
        payload = {"variety": "NORMAL", "orderid": broker_order_id}
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
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/details/{broker_order_id}",
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
