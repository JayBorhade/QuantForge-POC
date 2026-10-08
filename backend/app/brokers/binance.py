"""Canonical Binance Spot API execution adapter."""

from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from app.brokers.base import BrokerOrderRequest, BrokerOrderResult
from app.models.order import OrderType


class BinanceBrokerAdapter:
    BASE_URL = "https://api.binance.com"
    _TIMEOUT = httpx.Timeout(10.0)

    def __init__(self, api_key: str, api_secret: str, access_token: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance requires api_key and api_secret")
        return {"X-MBX-APIKEY": self.api_key}

    def _signed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "timestamp": int(time.time() * 1000)}
        query = urlencode(params)
        params["signature"] = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        return params

    @staticmethod
    def _status(value: str) -> str:
        return {
            "NEW": "submitted",
            "PENDING_NEW": "pending",
            "PARTIALLY_FILLED": "partially_filled",
            "FILLED": "filled",
            "CANCELED": "cancelled",
            "REJECTED": "rejected",
            "EXPIRED": "cancelled",
        }.get(value.upper(), "failed")

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/v3/account",
                    headers=self._headers(),
                    params=self._signed_params({"recvWindow": 5000}),
                )
                return response.status_code == 200
        except (httpx.HTTPError, ValueError):
            return False

    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        symbol = request.symbol.replace("/", "").upper()
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": request.side.value.upper(),
            "type": request.order_type.value.upper(),
            "quantity": format(request.quantity, "f"),
            "newClientOrderId": request.client_order_id,
        }
        if request.order_type is OrderType.LIMIT:
            if request.limit_price is None:
                raise ValueError("Binance LIMIT order requires limit_price")
            params.update({"price": format(request.limit_price, "f"), "timeInForce": "GTC"})

        params.update(request.broker_params)
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/order",
                headers=self._headers(),
                params=self._signed_params(params),
            )
            data = response.json()
            if response.status_code >= 400 or "orderId" not in data:
                raise RuntimeError(data.get("msg") or f"Binance order failed ({response.status_code})")
            return BrokerOrderResult(f"binance:{symbol}:{data['orderId']}", self._status(str(data.get("status", "NEW"))))

    @staticmethod
    def _parse_order_id(broker_order_id: str) -> tuple[str, str]:
        parts = broker_order_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "binance":
            raise ValueError("Invalid Binance broker order id")
        return parts[1], parts[2]

    async def cancel_order(self, broker_order_id: str) -> None:
        symbol, order_id = self._parse_order_id(broker_order_id)
        await self.cancel_order_for_symbol(symbol, order_id)

    async def cancel_order_for_symbol(self, symbol: str, broker_order_id: str) -> None:
        params = self._signed_params({"symbol": symbol.replace("/", "").upper(), "orderId": broker_order_id})
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.delete(
                f"{self.BASE_URL}/api/v3/order",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            if "orderId" not in data:
                raise RuntimeError(data.get("msg") or "Binance cancellation failed")

    async def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        symbol, order_id = self._parse_order_id(broker_order_id)
        return await self.get_order_for_symbol(symbol, order_id)

    async def get_order_for_symbol(self, symbol: str, broker_order_id: str) -> BrokerOrderResult:
        params = self._signed_params({"symbol": symbol.replace("/", "").upper(), "orderId": broker_order_id})
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/api/v3/order",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return BrokerOrderResult(
                broker_order_id=broker_order_id,
                status=self._status(str(data.get("status", ""))),
            )

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/api/v3/ticker/price",
                params={"symbol": symbol.replace("/", "").upper()},
            )
            response.raise_for_status()
            data = response.json()
            return {"symbol": symbol, "price": Decimal(str(data["price"])), "broker": "binance"}

    async def get_positions(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/api/v3/account",
                headers=self._headers(),
                params=self._signed_params({"recvWindow": 5000}),
            )
            response.raise_for_status()
            return response.json().get("balances", [])
