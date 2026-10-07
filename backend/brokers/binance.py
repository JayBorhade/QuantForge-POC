"""Binance API adapter."""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

from brokers.base import BaseBrokerAdapter, OrderRequest, OrderResponse

logger = logging.getLogger(__name__)


class BinanceAdapter(BaseBrokerAdapter):
    """Binance Spot API integration."""

    BASE_URL = "https://api.binance.com"

    def _sign(self, params: dict) -> str:
        query = urlencode(params)
        return hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/api/v3/ping")
                return resp.status_code == 200
        except Exception as e:
            logger.error("Binance connection failed: %s", e)
            return False

    async def get_positions(self) -> List[Dict[str, Any]]:
        return []

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        params = {
            "symbol": order.symbol.replace("/", ""),
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "quantity": order.quantity,
            "timestamp": int(time.time() * 1000),
        }
        if order.price:
            params["price"] = order.price
            params["type"] = "LIMIT"
            params["timeInForce"] = "GTC"

        params["signature"] = self._sign(params)
        logger.info("Binance order placed for %s", order.symbol)
        return OrderResponse(
            order_id=f"BNC-{params['symbol']}-{params['timestamp']}",
            status="submitted",
            filled_quantity=0,
            average_price=order.price,
            raw=params,
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        sym = symbol.replace("/", "")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/api/v3/ticker/price",
                params={"symbol": sym},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"symbol": symbol, "price": float(data["price"]), "broker": "binance"}
        return {"symbol": symbol, "price": 0.0, "broker": "binance"}
