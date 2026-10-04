"""Zerodha Kite API adapter."""

import logging
from typing import Any, Dict, List

from brokers.base import BaseBrokerAdapter, OrderRequest, OrderResponse

logger = logging.getLogger(__name__)


class ZerodhaAdapter(BaseBrokerAdapter):
    """Zerodha Kite Connect integration."""

    BASE_URL = "https://api.kite.trade"

    async def connect(self) -> bool:
        logger.info("Connecting to Zerodha Kite API")
        return bool(self.access_token)

    async def get_positions(self) -> List[Dict[str, Any]]:
        # Production: kite.positions()
        return []

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        logger.info("Zerodha order: %s %s %s", order.side, order.quantity, order.symbol)
        return OrderResponse(
            order_id=f"ZRD-{order.symbol}-{order.side}",
            status="pending",
            filled_quantity=0,
            average_price=None,
            raw={"broker": "zerodha", "symbol": order.symbol},
        )

    async def cancel_order(self, order_id: str) -> bool:
        logger.info("Cancelling Zerodha order %s", order_id)
        return True

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "ltp": 0.0, "broker": "zerodha"}
